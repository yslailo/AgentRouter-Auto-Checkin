#!/bin/bash
# setup-proxy.sh - 代理节点解析与 sing-box 启动
# 环境变量: NODE_LINK（必填）- 单个代理节点链接
export LC_ALL=C
set -e

export NODE_LINK=${NODE_LINK:-''}

if [ -z "$NODE_LINK" ]; then
  echo "[INFO] 未配置代理节点（NODE_LINK），跳过代理设置"
  exit 0
fi

# 检查依赖
if ! command -v jq &> /dev/null; then
  echo "[INFO] 安装 jq..."
  sudo apt-get update -qq && sudo apt-get install -y jq > /dev/null
fi

# 检查下载工具
command -v curl &>/dev/null && COMMAND="curl -sLo" || command -v wget &>/dev/null && COMMAND="wget -qO" || { echo "[ERROR] 需要 curl 或 wget"; exit 1; }

echo "[INFO] 获取 sing-box 最新版本..."
latest_version=$(curl -s "https://api.github.com/repos/SagerNet/sing-box/releases" | jq -r '[.[] | select(.prerelease==false)][0].tag_name | sub("^v"; "")')
if [ -z "$latest_version" ]; then
  echo "[WARN] 无法获取最新版本，使用 v1.13.14"
  latest_version="1.13.14"
fi
echo "[INFO] 使用版本: v${latest_version}"

ARCH_RAW=$(uname -m)
case "${ARCH_RAW}" in
    'x86_64' | 'amd64')  ARCH='amd64' ;;
    'x86' | 'i686' | 'i386') ARCH='386' ;;
    'aarch64' | 'arm64') ARCH='arm64' ;;
    'armv7l')  ARCH='armv7' ;;
    's390x')   ARCH='s390x' ;;
    *) echo "[ERROR] 不支持的架构: ${ARCH_RAW}"; exit 1 ;;
esac

echo "[INFO] 下载 sing-box..."
$COMMAND sing-box.tar.gz "https://github.com/SagerNet/sing-box/releases/download/v${latest_version}/sing-box-${latest_version}-linux-${ARCH}.tar.gz"
tar -xzf sing-box.tar.gz
mv "sing-box-${latest_version}-linux-${ARCH}/sing-box" ./
rm -rf sing-box.tar.gz "sing-box-${latest_version}-linux-${ARCH}"
chmod +x sing-box

# 解析协议
proto=$(echo "$NODE_LINK" | cut -d':' -f1)
content="${NODE_LINK#*://}"
content="${content%%#*}"

echo "[INFO] 解析协议: $proto"

# URL 解码函数
url_decode() {
  local encoded="$1"
  printf '%b' "$(echo "$encoded" | sed 's/%/\\x/g')"
}

# 初始化变量
outbound_type=""
outbound_server=""
outbound_port=""
outbound_uuid=""
outbound_flow=""
outbound_transport_type="tcp"
outbound_path="/"
outbound_host=""
outbound_security="none"
outbound_sni=""
outbound_fingerprint="chrome"
outbound_reality_pbk=""
outbound_reality_sid=""
outbound_password=""
outbound_up_mbps=100
outbound_down_mbps=100
outbound_obfs_password=""
outbound_auth=""
outbound_congestion="bbr"
outbound_udp_over_stream="true"
outbound_zerortt="false"
outbound_username=""
outbound_password2=""
outbound_version="5"
outbound_insecure="false"
outbound_alpn=""

case "$proto" in
  vless)
    uuid_host="${content}"
    uuid="${uuid_host%%@*}"
    rest="${uuid_host#*@}"
    if [[ "$rest" == *"?"* ]]; then
      host_port="${rest%%\?*}"
      query="${rest#*\?}"
    else
      host_port="$rest"
      query=""
    fi
    outbound_server="${host_port%:*}"
    outbound_port="${host_port#*:}"
    outbound_uuid="$uuid"
    outbound_type="vless"

    if [ -n "$query" ]; then
      flow=$(echo "$query" | grep -o 'flow=[^&]*' | cut -d= -f2)
      [ -n "$flow" ] && outbound_flow="$flow"
      ttype=$(echo "$query" | grep -o 'type=[^&]*' | cut -d= -f2)
      [ -n "$ttype" ] && outbound_transport_type="$ttype"
      path_raw=$(echo "$query" | grep -o 'path=[^&]*' | cut -d= -f2)
      if [ -n "$path_raw" ]; then
        path_decoded=$(url_decode "$path_raw")
        outbound_path="${path_decoded%%\?*}"
      fi
      host=$(echo "$query" | grep -o 'host=[^&]*' | cut -d= -f2)
      [ -n "$host" ] && outbound_host="$host"
      sec=$(echo "$query" | grep -o 'security=[^&]*' | cut -d= -f2)
      [ -n "$sec" ] && outbound_security="$sec"
      sni=$(echo "$query" | grep -o 'sni=[^&]*' | cut -d= -f2)
      [ -n "$sni" ] && outbound_sni="$sni"
      fp=$(echo "$query" | grep -o 'fp=[^&]*' | cut -d= -f2)
      [ -n "$fp" ] && outbound_fingerprint="$fp"
      pbk=$(echo "$query" | grep -o 'pbk=[^&]*' | cut -d= -f2)
      [ -n "$pbk" ] && outbound_reality_pbk="$pbk"
      sid=$(echo "$query" | grep -o 'sid=[^&]*' | cut -d= -f2)
      [ -n "$sid" ] && outbound_reality_sid="$sid"
      ins=$(echo "$query" | grep -o 'insecure=[^&]*' | cut -d= -f2)
      [ "$ins" = "1" ] || [ "$ins" = "true" ] && outbound_insecure="true"
      alins=$(echo "$query" | grep -o 'allowInsecure=[^&]*' | cut -d= -f2)
      [ "$alins" = "1" ] || [ "$alins" = "true" ] && outbound_insecure="true"
    fi
    [ -z "$outbound_host" ] && outbound_host="$outbound_server"
    [ -z "$outbound_sni" ] && outbound_sni="$outbound_server"
    ;;

  vmess)
    b64="${content}"
    mod=$(( ${#b64} % 4 ))
    if [ $mod -eq 2 ]; then b64="${b64}=="; elif [ $mod -eq 3 ]; then b64="${b64}="; fi
    decoded=$(echo "$b64" | base64 -d 2>/dev/null)
    if [ -z "$decoded" ]; then
      echo "[ERROR] VMess 解码失败"
      exit 1
    fi

    add=$(echo "$decoded" | jq -r '.add // ""')
    port=$(echo "$decoded" | jq -r '.port // 443')
    id=$(echo "$decoded" | jq -r '.id // ""')
    net=$(echo "$decoded" | jq -r '.net // "tcp"')
    tls=$(echo "$decoded" | jq -r '.tls // ""')
    sni=$(echo "$decoded" | jq -r '.sni // ""')
    host=$(echo "$decoded" | jq -r '.host // ""')
    path_raw=$(echo "$decoded" | jq -r '.path // "/"')
    path_decoded=$(url_decode "$path_raw")
    outbound_path="${path_decoded%%\?*}"
    fp=$(echo "$decoded" | jq -r '.fp // "chrome"')

    outbound_type="vmess"
    outbound_server="$add"
    outbound_port="$port"
    outbound_uuid="$id"
    outbound_transport_type="$net"
    outbound_host="${host:-$add}"
    outbound_sni="${sni:-$add}"
    outbound_fingerprint="$fp"
    outbound_security="$tls"
    ;;

  trojan)
    pass_rest="${content}"
    password="${pass_rest%%@*}"
    rest="${pass_rest#*@}"
    if [[ "$rest" == *"?"* ]]; then
      host_port="${rest%%\?*}"
      query="${rest#*\?}"
    else
      host_port="$rest"
      query=""
    fi
    outbound_server="${host_port%:*}"
    outbound_port="${host_port#*:}"
    outbound_password="$password"
    outbound_type="trojan"

    if [ -n "$query" ]; then
      ttype=$(echo "$query" | grep -o 'type=[^&]*' | cut -d= -f2)
      [ -n "$ttype" ] && outbound_transport_type="$ttype"
      path_raw=$(echo "$query" | grep -o 'path=[^&]*' | cut -d= -f2)
      if [ -n "$path_raw" ]; then
        path_decoded=$(url_decode "$path_raw")
        outbound_path="${path_decoded%%\?*}"
      fi
      host=$(echo "$query" | grep -o 'host=[^&]*' | cut -d= -f2)
      [ -n "$host" ] && outbound_host="$host"
      sni=$(echo "$query" | grep -o 'sni=[^&]*' | cut -d= -f2)
      [ -n "$sni" ] && outbound_sni="$sni"
      fp=$(echo "$query" | grep -o 'fp=[^&]*' | cut -d= -f2)
      [ -n "$fp" ] && outbound_fingerprint="$fp"
      ins=$(echo "$query" | grep -o 'insecure=[^&]*' | cut -d= -f2)
      [ "$ins" = "1" ] || [ "$ins" = "true" ] && outbound_insecure="true"
    fi
    [ -z "$outbound_host" ] && outbound_host="$outbound_server"
    [ -z "$outbound_sni" ] && outbound_sni="$outbound_server"
    ;;

  hysteria2|hy2)
    auth=""
    if [[ "$content" == *"@"* ]]; then
      auth="${content%%@*}"
      host_port="${content#*@}"
    else
      host_port="$content"
    fi
    if [[ "$host_port" == *"?"* ]]; then
      hp="${host_port%%\?*}"
      query="${host_port#*\?}"
    else
      hp="$host_port"
      query=""
    fi
    hp="${hp%/}"
    outbound_server="${hp%:*}"
    outbound_port="${hp#*:}"
    outbound_type="hysteria2"
    outbound_auth="$auth"

    if [ -n "$query" ]; then
      obfs=$(echo "$query" | grep -o 'obfs=[^&]*' | cut -d= -f2)
      [ -n "$obfs" ] && outbound_obfs_password="$obfs"
      sni=$(echo "$query" | grep -o 'sni=[^&]*' | cut -d= -f2)
      [ -n "$sni" ] && outbound_sni="$sni"
      ins=$(echo "$query" | grep -o 'insecure=[^&]*' | cut -d= -f2)
      [ "$ins" = "1" ] || [ "$ins" = "true" ] && outbound_insecure="true"
    fi
    [ -z "$outbound_sni" ] && outbound_sni="$outbound_server"
    ;;

  socks5|socks)
    if [[ "$content" == *"@"* ]]; then
      user_pass="${content%%@*}"
      host_port="${content#*@}"
      if [[ "$user_pass" == *":"* ]]; then
        outbound_username="${user_pass%:*}"
        outbound_password2="${user_pass#*:}"
      fi
    else
      host_port="$content"
    fi
    outbound_server="${host_port%:*}"
    outbound_port="${host_port#*:}"
    outbound_type="socks"
    ;;

  *)
    echo "[ERROR] 不支持的协议: $proto"
    exit 1
    ;;
esac

if [ -z "$outbound_server" ] || [ -z "$outbound_port" ]; then
  echo "[ERROR] 无法解析服务器地址或端口"
  exit 1
fi

echo "[INFO] 服务器: $outbound_server:$outbound_port"

# 构建 outbound JSON
jq_outbound="{\"type\":\"$outbound_type\",\"tag\":\"proxy\",\"server\":\"$outbound_server\",\"server_port\":$outbound_port"

case "$outbound_type" in
  vless)
    jq_outbound="$jq_outbound,\"uuid\":\"$outbound_uuid\""
    [ -n "$outbound_flow" ] && jq_outbound="$jq_outbound,\"flow\":\"$outbound_flow\""
    if [ "$outbound_transport_type" != "tcp" ]; then
      jq_outbound="$jq_outbound,\"transport\":{\"type\":\"$outbound_transport_type\",\"path\":\"$outbound_path\",\"headers\":{\"Host\":\"$outbound_host\"}}"
    fi
    tls_enabled="false"
    [ "$outbound_security" = "tls" ] || [ "$outbound_security" = "reality" ] && tls_enabled="true"
    tls_json="{\"enabled\":$tls_enabled,\"server_name\":\"$outbound_sni\",\"insecure\":$outbound_insecure,\"utls\":{\"enabled\":true,\"fingerprint\":\"$outbound_fingerprint\"}"
    [ "$outbound_security" = "reality" ] && tls_json="$tls_json,\"reality\":{\"enabled\":true,\"public_key\":\"$outbound_reality_pbk\",\"short_id\":\"$outbound_reality_sid\"}"
    tls_json="$tls_json}"
    jq_outbound="$jq_outbound,\"tls\":$tls_json"
    ;;

  vmess)
    jq_outbound="$jq_outbound,\"uuid\":\"$outbound_uuid\",\"security\":\"auto\""
    jq_outbound="$jq_outbound,\"transport\":{\"type\":\"$outbound_transport_type\",\"path\":\"$outbound_path\",\"headers\":{\"Host\":\"$outbound_host\"}}"
    tls_enabled="false"
    [ "$outbound_security" = "tls" ] && tls_enabled="true"
    jq_outbound="$jq_outbound,\"tls\":{\"enabled\":$tls_enabled,\"server_name\":\"$outbound_sni\",\"insecure\":$outbound_insecure,\"utls\":{\"enabled\":true,\"fingerprint\":\"$outbound_fingerprint\"}}"
    ;;

  trojan)
    jq_outbound="$jq_outbound,\"password\":\"$outbound_password\""
    jq_outbound="$jq_outbound,\"transport\":{\"type\":\"$outbound_transport_type\",\"path\":\"$outbound_path\",\"headers\":{\"Host\":\"$outbound_host\"}}"
    jq_outbound="$jq_outbound,\"tls\":{\"enabled\":true,\"server_name\":\"$outbound_sni\",\"insecure\":$outbound_insecure,\"utls\":{\"enabled\":true,\"fingerprint\":\"$outbound_fingerprint\"}}"
    ;;

  hysteria2)
    jq_outbound="$jq_outbound,\"up_mbps\":$outbound_up_mbps,\"down_mbps\":$outbound_down_mbps"
    [ -n "$outbound_obfs_password" ] && jq_outbound="$jq_outbound,\"obfs\":{\"type\":\"salamander\",\"password\":\"$outbound_obfs_password\"}"
    [ -n "$outbound_auth" ] && jq_outbound="$jq_outbound,\"password\":\"$outbound_auth\""
    jq_outbound="$jq_outbound,\"tls\":{\"enabled\":true,\"server_name\":\"$outbound_sni\",\"insecure\":$outbound_insecure}"
    ;;

  socks)
    [ -n "$outbound_username" ] && jq_outbound="$jq_outbound,\"username\":\"$outbound_username\""
    [ -n "$outbound_password2" ] && jq_outbound="$jq_outbound,\"password\":\"$outbound_password2\""
    jq_outbound="$jq_outbound,\"version\":\"$outbound_version\""
    ;;
esac
jq_outbound="$jq_outbound}"

# 生成 sing-box 配置
cat << EOF > sing-box-config.json
{
  "log": {"level": "warn"},
  "inbounds": [
    {"type": "socks", "tag": "socks-in", "listen": "127.0.0.1", "listen_port": 1080},
    {"type": "http", "tag": "http-in", "listen": "127.0.0.1", "listen_port": 1081}
  ],
  "outbounds": [$jq_outbound]
}
EOF

if ! jq empty sing-box-config.json 2>/dev/null; then
  echo "[ERROR] 生成的配置无效"
  exit 1
fi

echo "[INFO] ✅ 配置已生成"

# 清理旧进程
pkill -f sing-box 2>/dev/null || true
fuser -k 1080/tcp 2>/dev/null || true
sleep 2

# 启动 sing-box
echo "[INFO] 启动 sing-box..."
./sing-box run -c sing-box-config.json > sing-box.log 2>&1 &
sleep 5

if ! pgrep -f sing-box > /dev/null; then
  echo "[ERROR] sing-box 启动失败"
  cat sing-box.log
  exit 1
fi

# 测试连接
echo "[INFO] 测试代理连接..."
for i in {1..3}; do
  if curl -x socks5://127.0.0.1:1080 -s --max-time 15 https://api.ipify.org > /dev/null 2>&1; then
    echo "[SUCCESS] ✅ 代理连接成功"
    echo "PROXY_SERVER=socks5://127.0.0.1:1080" >> $GITHUB_ENV
    exit 0
  fi
  echo "[WARN] 尝试 $i/3..."
  sleep 3
done

echo "[ERROR] ❌ 代理连接失败"
echo "---- sing-box 日志 ----"
cat sing-box.log
exit 1
