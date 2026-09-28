import re

path = r'c:\Users\hassa\Desktop\New folder (21)\mcdis\dashboard\templates\index.html'

with open(path, encoding='utf-8') as f:
    content = f.read()

# Find and replace the attemptLogin function
old_pattern = r'function attemptLogin\(\) \{.*?\}'
new_func = '''async function attemptLogin() {
    const user = document.getElementById('rbac-user').value.trim();
    const pin  = document.getElementById('rbac-pin').value.trim();
    const err  = document.getElementById('rbac-error');
    if (!user || !pin) { err.textContent = 'ENTER CREDENTIALS'; return; }
    err.style.color = '#00e5ff';
    err.textContent = 'AUTHENTICATING...';
    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: user, pin_code: pin})
        });
        const d = await res.json();
        if (d.status === 'SUCCESS') {
            operatorRole = d.role;
            document.getElementById('rbac-overlay').style.display = 'none';
            const rank = document.getElementById('op-rank-display');
            if (rank) rank.textContent = operatorRole;
            const enc = document.getElementById('footer-enc-status');
            if (enc) enc.textContent = 'TLS 1.3 SECURE';
        } else {
            err.style.color = '#ff4444';
            err.textContent = 'ACCESS DENIED';
        }
    } catch(e) {
        err.style.color = '#ff4444';
        err.textContent = 'SERVER ERROR: ' + e.message;
    }
}'''

new_content, count = re.subn(old_pattern, new_func, content, flags=re.DOTALL)

if count > 0:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"SUCCESS: Replaced {count} occurrence(s) of attemptLogin")
else:
    print("ERROR: Pattern not found")
    idx = content.find('attemptLogin')
    print(f"  Found 'attemptLogin' at index: {idx}")
    print(f"  Context: {repr(content[idx:idx+100])}")
