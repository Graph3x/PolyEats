#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$root"

echo "geocoding (go)"
protoc -I . \
  --go_out=services/geocoding --go_opt=paths=source_relative \
  --go-grpc_out=services/geocoding --go-grpc_opt=paths=source_relative \
  proto/geocoding.proto

echo "auth (go)"
protoc -I . \
  --go_out=services/auth --go_opt=paths=source_relative \
  --go-grpc_out=services/auth --go-grpc_opt=paths=source_relative \
  proto/auth.proto

echo "gateway (go)"
protoc -I . \
  --go_out=services/gateway --go_opt=paths=source_relative \
  --go-grpc_out=services/gateway --go-grpc_opt=paths=source_relative \
  proto/auth.proto

echo "order-tracking (python)"
python -m grpc_tools.protoc -I proto \
  --python_out=services/order-tracking \
  --pyi_out=services/order-tracking \
  --grpc_python_out=services/order-tracking \
  proto/geocoding.proto

echo "address (proto copy)"
mkdir -p services/address/src/main/proto
cp proto/geocoding.proto services/address/src/main/proto/geocoding.proto
