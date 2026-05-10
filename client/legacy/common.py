import struct
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 协议常量
HEADER_FORMAT = '!II'  # 两个无符号整型: stream_id, data_len
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

def encode_packet(stream_id: int, data: bytes) -> bytes:
    """将数据编码成数据包格式: stream_id + data_len + data"""
    return struct.pack(HEADER_FORMAT, stream_id, len(data)) + data

def decode_packet(data: bytes):
    """从数据中解码出 stream_id, data_len, 和剩余数据（可能不完整）"""
    if len(data) < HEADER_SIZE:
        return None, None, data
    stream_id, data_len = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
    if len(data) < HEADER_SIZE + data_len:
        return None, None, data
    packet_data = data[HEADER_SIZE:HEADER_SIZE+data_len]
    remaining = data[HEADER_SIZE+data_len:]
    return stream_id, packet_data, remaining
