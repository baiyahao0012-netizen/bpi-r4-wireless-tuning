"=== 笔记本 HTTP 测试 ==="
try {
    $r = Invoke-WebRequest -Uri "http://www.baidu.com" -UseBasicParsing -TimeoutSec 8
    "HTTP " + $r.StatusCode + " OK"
} catch {
    "HTTP FAIL: " + $_.Exception.Message
}
"=== DNS ==="
nslookup pypi.tuna.tsinghua.edu.cn 2>&1 | Select-Object -Last 4
