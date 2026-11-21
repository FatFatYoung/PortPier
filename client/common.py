"""
PortPier shared protocol module.

Packet format: [stream_id:uint32][data_len:uint32][data]
Also provides TLS context builders for the control/data channel.
"""
import struct
import ssl
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 协议常量
HEADER_FORMAT = '!II'  # 两个无符号整型: stream_id, data_len
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# 单包声明长度硬上限。正常发送方按 <=64KiB 分块读写；对端声明超过上限
# 即视为协议违规并断开连接，防止恶意声明超大长度耗尽内存。
MAX_PACKET_SIZE = 1024 * 1024

# 每条流的有界数据队列深度（块数）：消费慢时形成背压，避免无界积压内存。
STREAM_QUEUE_MAXSIZE = 64


def encode_packet(stream_id: int, data: bytes) -> bytes:
    """将数据编码成数据包格式: stream_id + data_len + data"""
    return struct.pack(HEADER_FORMAT, stream_id, len(data)) + data


def decode_packet(data: bytes):
    """从数据中解码出 stream_id, data, 和剩余数据（可能不完整）。

    数据不完整时返回 (None, None, data)；声明长度超过 MAX_PACKET_SIZE 时
    抛出 ValueError（调用方应断开该连接）。
    """
    if len(data) < HEADER_SIZE:
        return None, None, data
    stream_id, data_len = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
    if data_len > MAX_PACKET_SIZE:
        raise ValueError("packet too large: %d bytes (limit %d)" % (data_len, MAX_PACKET_SIZE))
    if len(data) < HEADER_SIZE + data_len:
        return None, None, data
    packet_data = data[HEADER_SIZE:HEADER_SIZE + data_len]
    remaining = data[HEADER_SIZE + data_len:]
    return stream_id, packet_data, remaining


def build_server_ssl_context(certfile: str, keyfile: str) -> ssl.SSLContext:
    """构建控制通道服务端 TLS 上下文。

    缺少证书/私钥配置时直接抛错，绝不静默降级为明文。
    """
    if not certfile or not keyfile:
        raise ValueError("TLS enabled but tls_certfile / tls_keyfile is not configured")
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile, keyfile)
    return ctx


def build_client_ssl_context(ca_file: str = '', insecure_skip_verify: bool = False) -> ssl.SSLContext:
    """构建隧道客户端 TLS 上下文。

    默认校验服务端证书（系统 CA + 可选 ca_file）；
    insecure_skip_verify 需显式开启：传输仍加密，但不验证对端身份。
    """
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    if ca_file:
        ctx.load_verify_locations(cafile=ca_file)
    if insecure_skip_verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx
