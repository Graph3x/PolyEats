import grpc


def grpc_channel(addr):
    return grpc.insecure_channel(addr)
