from flask import Flask, request, jsonify
import hmac
import hashlib
import time
import json
import logging
from datetime import datetime
from urllib.parse import parse_qs

app = Flask(__name__)

WEBHOOK_SECRET = "wh_sk_2024_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
INCLUDE_SELF_MESSAGE = True

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("webhook.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 旧版签名：HMAC-SHA256(secret, timestamp + payload)
def verify_signature_legacy(raw_data: bytes, signature: str, secret: str, timestamp_str: str) -> bool:
    if not signature or not timestamp_str:
        return False
    mac = hmac.new(secret.encode('utf-8'), digestmod=hashlib.sha256)
    mac.update(timestamp_str.encode('utf-8'))
    mac.update(raw_data)
    expected_signature = mac.hexdigest()
    return hmac.compare_digest(expected_signature, signature)

# Promax08 签名：HMAC-SHA256(secret, f"{Wxid}:{MessageType}:{Timestamp}")
def verify_signature_promax(parsed_json: dict, signature: str, secret: str) -> bool:
    try:
        if not isinstance(parsed_json, dict):
            return False
        wxid = parsed_json.get('Wxid')
        msg_type = parsed_json.get('MessageType')
        ts = parsed_json.get('Timestamp')
        if wxid is None or msg_type is None or ts is None:
            return False
        sign_str = f"{wxid}:{msg_type}:{int(ts)}"
        mac = hmac.new(secret.encode('utf-8'), digestmod=hashlib.sha256)
        mac.update(sign_str.encode('utf-8'))
        expected_signature = mac.hexdigest()
        return hmac.compare_digest(expected_signature, str(signature))
    except Exception:
        return False

# 自动格式化所有字段
def pretty_format(data, indent=0):
    spacing = '  ' * indent
    if isinstance(data, dict):
        result = ""
        for key, value in data.items():
            result += f"{spacing}- {key}:"
            if isinstance(value, (dict, list)):
                result += "\n" + pretty_format(value, indent + 1)
            else:
                result += f" {value}\n"
        return result
    elif isinstance(data, list):
        result = ""
        for idx, item in enumerate(data):
            result += f"{spacing}- [{idx}]:\n" + pretty_format(item, indent + 1)
        return result
    else:
        return f"{spacing}{data}\n"

# 格式化日志输出
def format_message(data):
    timestamp = None
    # 支持顶层 Timestamp、timestamp、ts
    for key in ('Timestamp', 'timestamp', 'ts'):
        if isinstance(data, dict) and key in data:
            timestamp = data.get(key)
            break
    try:
        if isinstance(timestamp, (int, float)):
            time_str = datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(timestamp, str) and timestamp.isdigit():
            time_str = datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d %H:%M:%S")
        else:
            time_str = str(timestamp)
    except Exception:
        time_str = str(timestamp)

    return (
        f"\n✅ Received webhook message at {time_str}:\n"
        f"{pretty_format(data)}"
    )

# 解析头部别名
def get_header_alias(headers, names):
    for n in names:
        v = headers.get(n)
        if v:
            return v
    return None

# 解析可能的 query/body 兜底字段
def extract_fallbacks(raw_data: bytes):
    ts = None
    sig = None
    # query
    try:
        if request.query_string:
            qs = parse_qs(request.query_string.decode('utf-8', errors='ignore'))
            for key in ('timestamp', 'ts'):
                if key in qs and qs[key]:
                    ts = qs[key][0]
                    break
            for key in ('sign', 'signature'):
                if key in qs and qs[key]:
                    sig = qs[key][0]
                    break
    except Exception:
        pass
    # body
    try:
        body_json = json.loads(raw_data.decode('utf-8')) if raw_data else {}
        if isinstance(body_json, dict):
            if ts is None:
                for key in ('Timestamp', 'timestamp', 'ts', 'timestamp_ms'):
                    if key in body_json:
                        ts = str(body_json[key])
                        break
            if sig is None:
                for key in ('Signature', 'signature', 'sign'):
                    if key in body_json:
                        sig = str(body_json[key])
                        break
        return ts, sig, body_json
    except Exception:
        return ts, sig, None

# Webhook 接口
@app.route('/webhook', methods=['POST', 'HEAD'])
def webhook():
    if request.method == 'HEAD':
        # 健康检查，直接返回200
        return '', 200

    raw_data = request.data
    headers = request.headers

    # 记录请求头和部分body（可选，生产可注释）
    logging.info(f"[Request Headers] {dict(headers)}")
    try:
        logging.info(f"[Request Body] {raw_data[:500].decode('utf-8', errors='ignore')}")
    except Exception as e:
        logging.warning(f"[Request Body decode error]: {e}")

    # 别名头
    signature = get_header_alias(headers, ['X-Webhook-Signature', 'X-Signature', 'Signature', 'Sign'])
    timestamp = get_header_alias(headers, ['X-Webhook-Timestamp', 'X-Timestamp', 'Timestamp'])

    # 兜底：query/body
    fb_ts, fb_sig, body_json = extract_fallbacks(raw_data)
    if timestamp is None:
        timestamp = fb_ts
    if signature is None:
        signature = fb_sig

    if WEBHOOK_SECRET:
        if not signature or not timestamp:
            logging.warning("❌ Missing signature or timestamp (after alias + fallback)")
            return jsonify({"status": "error", "message": "Missing signature or timestamp"}), 400
        try:
            # 先尝试 Promax08 签名（要求 body 为 WebhookMessage 结构）
            promax_ok = False
            parsed_json = None
            if body_json is not None:
                parsed_json = body_json if isinstance(body_json, dict) else None
                if parsed_json:
                    promax_ok = verify_signature_promax(parsed_json, signature, WEBHOOK_SECRET)

            # 再尝试旧版签名（timestamp + 原始 body）
            legacy_ok = verify_signature_legacy(raw_data, signature, WEBHOOK_SECRET, str(timestamp))

            if not (promax_ok or legacy_ok):
                logging.warning("❌ Signature verification failed (legacy+promax both failed)")
                return jsonify({"status": "error", "message": "Invalid signature"}), 403
        except Exception as e:
            logging.error(f"❌ Signature verify exception: {e}")
            return jsonify({"status": "error", "message": "Signature verify exception"}), 400

    try:
        data = body_json if isinstance(body_json, dict) else request.get_json(force=True)

        if not INCLUDE_SELF_MESSAGE and isinstance(data, dict) and data.get('isSelf'):
            return jsonify({"status": "ignored", "reason": "self message skipped"}), 200

        formatted = format_message(data)
        logging.info(formatted)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logging.exception("❌ Error processing webhook:")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    logging.info("🚀 Webhook server is running on port 8000...")
    app.run(host='0.0.0.0', port=8000)

