#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
platform_chart="$repo_root/charts/platform"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

for command in helm ruby; do
  command -v "$command" >/dev/null || {
    echo "required command is missing: $command" >&2
    exit 1
  }
done

helm dependency update "$platform_chart"

for chart in store woo-mcp aux-mcp gateway platform-db dashboard; do
  helm lint "$repo_root/charts/$chart"
done
helm lint "$platform_chart" -f "$platform_chart/values-local.yaml"
helm lint "$platform_chart" -f "$platform_chart/values-vps.yaml"

local_manifest="$tmp_dir/local.yaml"
vps_manifest="$tmp_dir/vps.yaml"
helm template urumi "$platform_chart" --namespace platform \
  -f "$platform_chart/values-local.yaml" >"$local_manifest"
helm template urumi "$platform_chart" --namespace platform \
  -f "$platform_chart/values-vps.yaml" >"$vps_manifest"

validate_manifest() {
  local manifest="$1"
  local environment="$2"
  ruby -ryaml - "$manifest" "$environment" <<'RUBY'
path, environment = ARGV
documents = YAML.load_stream(File.read(path)).compact
abort "rendered a Kubernetes Secret" if documents.any? { |item| item["kind"] == "Secret" }

services = documents.select { |item| item["kind"] == "Service" }
expected_services = {
  "wordpress" => ["store", 80],
  "mariadb" => ["store", 3306],
  "woocommerce-mcp" => ["mcp", 8000],
  "currency-mcp" => ["mcp", 8000],
  "policy-mcp" => ["mcp", 8000],
  "gateway" => ["platform", 8000],
  "postgres" => ["platform", 5432],
  "dashboard" => ["platform", 80],
}
actual_services = services.to_h do |item|
  [item.dig("metadata", "name"), [item.dig("metadata", "namespace"), item.dig("spec", "ports", 0, "port")]]
end
abort "service contract mismatch: #{actual_services.inspect}" unless actual_services == expected_services
abort "non-ClusterIP service rendered" unless services.all? { |item| item.dig("spec", "type") == "ClusterIP" }

ingresses = documents.select { |item| item["kind"] == "Ingress" }
abort "unexpected ingress set" unless ingresses.map { |item| item.dig("metadata", "name") }.sort == %w[dashboard gateway shop]
abort "private MCP service exposed by Ingress" if ingresses.any? do |item|
  item.dig("spec", "rules").to_a.any? do |rule|
    rule.dig("http", "paths").to_a.any? do |entry|
      %w[woocommerce-mcp currency-mcp policy-mcp].include?(entry.dig("backend", "service", "name"))
    end
  end
end

expected_hosts = if environment == "local"
  {"shop" => "shop.127.0.0.1.nip.io", "dashboard" => "app.127.0.0.1.nip.io", "gateway" => "app.127.0.0.1.nip.io"}
else
  {"shop" => "shop.example.com", "dashboard" => "app.example.com", "gateway" => "app.example.com"}
end
ingresses.each do |item|
  name = item.dig("metadata", "name")
  abort "wrong host for #{name}" unless item.dig("spec", "rules", 0, "host") == expected_hosts.fetch(name)
  has_tls = !item.dig("spec", "tls").to_a.empty?
  abort "wrong TLS state for #{name}" unless has_tls == (environment == "vps")
end

puts "PASS #{environment} manifest: namespaces, services, ingress, TLS, and private MCP exposure"
RUBY
}

validate_manifest "$local_manifest" local
validate_manifest "$vps_manifest" vps

if grep -R --include='values*.yaml' -nE 'tag:[[:space:]]*["'\'']?latest(["'\'']|$)' \
  "$repo_root/charts"; then
  echo "mutable latest image tag is forbidden" >&2
  exit 1
fi

if helm template urumi "$platform_chart" --namespace platform \
  -f "$platform_chart/values-local.yaml" \
  --set 'woo-mcp.existingSecret=' >"$tmp_dir/negative.yaml" 2>"$tmp_dir/negative.err"; then
  echo "missing existingSecret negative test unexpectedly rendered" >&2
  exit 1
fi
grep -Fq "woo-mcp.existingSecret is required" "$tmp_dir/negative.err"
echo "PASS missing existingSecret rejected"

echo "PASS Helm chart contract checks"
