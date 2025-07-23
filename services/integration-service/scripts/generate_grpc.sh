#!/bin/bash

# Generate Python gRPC code from proto files

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
PROTO_DIR="$PROJECT_ROOT/src/grpc"
OUT_DIR="$PROJECT_ROOT/src/grpc"

echo "Generating gRPC code from proto files..."

# Install required packages if not already installed
pip install grpcio-tools grpcio-reflection

# Generate Python code
python -m grpc_tools.protoc \
    -I"$PROTO_DIR" \
    --python_out="$OUT_DIR" \
    --grpc_python_out="$OUT_DIR" \
    "$PROTO_DIR/integration_service.proto"

# Fix imports in generated files
echo "Fixing imports in generated files..."

# Replace absolute imports with relative imports
sed -i '' 's/^import integration_service_pb2/from . import integration_service_pb2/' "$OUT_DIR/integration_service_pb2_grpc.py"

echo "gRPC code generation complete!"
echo "Generated files:"
echo "  - $OUT_DIR/integration_service_pb2.py"
echo "  - $OUT_DIR/integration_service_pb2_grpc.py"