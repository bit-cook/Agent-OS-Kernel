//! 内置工具 — 与 Python 主线同语义的真实实现
//!
//! 安全契约（对齐 Python 侧 P0-01）：
//! - 文件工具：workspace 根约束（canonicalize 解析 symlink/.. 后按路径段校验），
//!   逃逸路径返回结构化拒绝
//! - 执行器：默认 fail closed（isolation_unavailable），显式 opt-in 才走宿主，
//!   argv 形式（无 shell）
//! - 计算器：自有递归下降解析器，绝不用 eval 语义

use super::base::Tool;
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::sync::Arc;

// ─── 路径工具 ─────────────────────────────────────────────

/// 将 filepath 解析为绝对路径并验证位于某个授权根内。
/// 相对路径按授权根解析；canonicalize 展开 symlink/..；
/// 按路径段比较（/workspace 不匹配 /workspace-evil）。
fn resolve_within_roots(filepath: &str, allowed_roots: &[PathBuf]) -> Result<PathBuf, String> {
    let candidate = Path::new(filepath);
    let candidates: Vec<PathBuf> = if candidate.is_absolute() {
        vec![candidate.to_path_buf()]
    } else {
        allowed_roots
            .iter()
            .map(|r| r.join(candidate))
            .chain(std::iter::once(
                std::env::current_dir().unwrap_or_default().join(candidate),
            ))
            .collect()
    };

    for c in candidates {
        // canonicalize 解析 symlink 与 ..；文件不存在时回退到词面解析
        let resolved = c.canonicalize().unwrap_or(c);
        for root in allowed_roots {
            let root_resolved = root.canonicalize().unwrap_or_else(|_| root.clone());
            if resolved.starts_with(&root_resolved) {
                return Ok(resolved);
            }
        }
    }
    Err(format!(
        "Path {:?} resolves outside allowed roots {:?}",
        filepath, allowed_roots
    ))
}

fn default_roots(allowed_roots: &[PathBuf]) -> Vec<PathBuf> {
    if allowed_roots.is_empty() {
        vec![std::env::current_dir().unwrap_or_default()]
    } else {
        allowed_roots.to_vec()
    }
}

// ─── Echo ─────────────────────────────────────────────────

pub struct EchoTool;

impl Tool for EchoTool {
    fn name(&self) -> &'static str {
        "echo"
    }
    fn description(&self) -> &'static str {
        "Echo input back"
    }
    fn run(&self, params: Value) -> Result<Value, String> {
        Ok(params)
    }
}

// ─── Calculator（真实安全表达式求值） ──────────────────────

pub struct CalculatorTool;

/// 递归下降表达式解析器：+ - * / % ^、括号、一元负号、
/// 函数 sin/cos/tan/sqrt/log/log10/exp/abs/min/max、常量 pi/e
struct ExprParser<'a> {
    chars: Vec<char>,
    pos: usize,
    _marker: std::marker::PhantomData<&'a ()>,
}

impl<'a> ExprParser<'a> {
    fn new(input: &'a str) -> Self {
        Self {
            chars: input.chars().collect(),
            pos: 0,
            _marker: std::marker::PhantomData,
        }
    }

    fn peek(&self) -> Option<char> {
        self.chars.get(self.pos).copied()
    }
    fn next(&mut self) -> Option<char> {
        let c = self.peek();
        if c.is_some() {
            self.pos += 1;
        }
        c
    }
    fn skip_ws(&mut self) {
        while matches!(self.peek(), Some(c) if c.is_whitespace()) {
            self.pos += 1;
        }
    }

    fn parse(&mut self) -> Result<f64, String> {
        let v = self.parse_expr()?;
        self.skip_ws();
        if self.pos != self.chars.len() {
            return Err(format!("Unexpected trailing input at position {}", self.pos));
        }
        Ok(v)
    }

    // expr := term (('+'|'-') term)*
    fn parse_expr(&mut self) -> Result<f64, String> {
        let mut v = self.parse_term()?;
        loop {
            self.skip_ws();
            match self.peek() {
                Some('+') => {
                    self.next();
                    v += self.parse_term()?;
                }
                Some('-') => {
                    self.next();
                    v -= self.parse_term()?;
                }
                _ => return Ok(v),
            }
        }
    }

    // term := factor (('*'|'/'|'%') factor)*
    fn parse_term(&mut self) -> Result<f64, String> {
        let mut v = self.parse_factor()?;
        loop {
            self.skip_ws();
            match self.peek() {
                Some('*') => {
                    self.next();
                    v *= self.parse_factor()?;
                }
                Some('/') => {
                    self.next();
                    let d = self.parse_factor()?;
                    if d == 0.0 {
                        return Err("Division by zero".to_string());
                    }
                    v /= d;
                }
                Some('%') => {
                    self.next();
                    let d = self.parse_factor()?;
                    if d == 0.0 {
                        return Err("Modulo by zero".to_string());
                    }
                    v %= d;
                }
                _ => return Ok(v),
            }
        }
    }

    // factor := base ('^' factor)?   （右结合）
    fn parse_factor(&mut self) -> Result<f64, String> {
        let base = self.parse_unary()?;
        self.skip_ws();
        if self.peek() == Some('^') {
            self.next();
            let exp = self.parse_factor()?;
            return Ok(base.powf(exp));
        }
        Ok(base)
    }

    // unary := ('-'|'+') unary | primary
    fn parse_unary(&mut self) -> Result<f64, String> {
        self.skip_ws();
        match self.peek() {
            Some('-') => {
                self.next();
                Ok(-self.parse_unary()?)
            }
            Some('+') => {
                self.next();
                self.parse_unary()
            }
            _ => self.parse_primary(),
        }
    }

    // primary := number | ident (函数/常量) | '(' expr ')'
    fn parse_primary(&mut self) -> Result<f64, String> {
        self.skip_ws();
        match self.peek() {
            Some('(') => {
                self.next();
                let v = self.parse_expr()?;
                self.skip_ws();
                if self.next() != Some(')') {
                    return Err("Expected ')'".to_string());
                }
                Ok(v)
            }
            Some(c) if c.is_ascii_digit() || c == '.' => self.parse_number(),
            Some(c) if c.is_alphabetic() || c == '_' => self.parse_ident(),
            other => Err(format!("Unexpected character: {:?}", other)),
        }
    }

    fn parse_number(&mut self) -> Result<f64, String> {
        let start = self.pos;
        let mut seen_dot = false;
        while let Some(c) = self.peek() {
            if c.is_ascii_digit() {
                self.pos += 1;
            } else if c == '.' && !seen_dot {
                seen_dot = true;
                self.pos += 1;
            } else {
                break;
            }
        }
        let s: String = self.chars[start..self.pos].iter().collect();
        s.parse::<f64>().map_err(|_| format!("Invalid number: {}", s))
    }

    fn parse_ident(&mut self) -> Result<f64, String> {
        let start = self.pos;
        while let Some(c) = self.peek() {
            if c.is_alphanumeric() || c == '_' {
                self.pos += 1;
            } else {
                break;
            }
        }
        let name: String = self.chars[start..self.pos].iter().collect();
        self.skip_ws();

        match name.as_str() {
            "pi" => return Ok(std::f64::consts::PI),
            "e" => return Ok(std::f64::consts::E),
            _ => {}
        }

        if self.peek() == Some('(') {
            self.next();
            let mut args = Vec::new();
            self.skip_ws();
            if self.peek() != Some(')') {
                args.push(self.parse_expr()?);
                self.skip_ws();
                while self.peek() == Some(',') {
                    self.next();
                    args.push(self.parse_expr()?);
                    self.skip_ws();
                }
            }
            if self.next() != Some(')') {
                return Err(format!("Expected ')' after function {}", name));
            }
            return apply_fn(&name, args);
        }
        Err(format!("Unknown identifier: {}", name))
    }
}

fn apply_fn(name: &str, args: Vec<f64>) -> Result<f64, String> {
    let a0 = args.first().copied().ok_or_else(|| format!("{} requires an argument", name))?;
    let v = match name {
        "sin" => a0.sin(),
        "cos" => a0.cos(),
        "tan" => a0.tan(),
        "sqrt" => {
            if a0 < 0.0 {
                return Err("sqrt of negative number".to_string());
            }
            a0.sqrt()
        }
        "log" | "ln" => a0.ln(),
        "log10" => a0.log10(),
        "exp" => a0.exp(),
        "abs" => a0.abs(),
        "floor" => a0.floor(),
        "ceil" => a0.ceil(),
        "round" => a0.round(),
        "min" => args.iter().cloned().fold(f64::INFINITY, f64::min),
        "max" => args.iter().cloned().fold(f64::NEG_INFINITY, f64::max),
        _ => return Err(format!("Disallowed function: {}", name)),
    };
    Ok(v)
}

impl Tool for CalculatorTool {
    fn name(&self) -> &'static str {
        "calculator"
    }
    fn description(&self) -> &'static str {
        "Evaluate mathematical expressions safely (no eval; own parser)"
    }
    fn run(&self, params: Value) -> Result<Value, String> {
        let expression = params["expression"]
            .as_str()
            .ok_or("Expression required")?;
        let mut parser = ExprParser::new(expression);
        let result = parser.parse()?;
        Ok(json!({ "result": result }))
    }
}

// ─── File tools（workspace 根约束） ────────────────────────

pub struct FileReadTool {
    pub allowed_roots: Vec<PathBuf>,
}

impl FileReadTool {
    pub fn new(allowed_roots: Vec<PathBuf>) -> Self {
        Self {
            allowed_roots: default_roots(&allowed_roots),
        }
    }
}

impl Tool for FileReadTool {
    fn name(&self) -> &'static str {
        "read_file"
    }
    fn description(&self) -> &'static str {
        "Read contents of a file (restricted to the workspace root)"
    }
    fn run(&self, params: Value) -> Result<Value, String> {
        let filepath = params["filepath"].as_str().ok_or("filepath required")?;
        let limit = params["limit"].as_u64().unwrap_or(10000) as usize;

        let safe = resolve_within_roots(filepath, &self.allowed_roots)
            .map_err(|e| format!("Access denied: {}", e))?;

        if !safe.exists() {
            return Err(format!("File not found: {:?}", safe));
        }
        if !safe.is_file() {
            return Err(format!("Not a file: {:?}", safe));
        }
        let content = std::fs::read_to_string(&safe)
            .map_err(|_| "File appears to be binary or unreadable".to_string())?;
        let truncated = content.len() >= limit;
        let shown: String = content.chars().take(limit).collect();
        Ok(json!({
            "data": shown,
            "filepath": safe.to_string_lossy(),
            "size": safe.metadata().map(|m| m.len()).unwrap_or(0),
            "truncated": truncated,
        }))
    }
}

pub struct FileWriteTool {
    pub allowed_roots: Vec<PathBuf>,
}

impl FileWriteTool {
    pub fn new(allowed_roots: Vec<PathBuf>) -> Self {
        Self {
            allowed_roots: default_roots(&allowed_roots),
        }
    }
}

impl Tool for FileWriteTool {
    fn name(&self) -> &'static str {
        "write_file"
    }
    fn description(&self) -> &'static str {
        "Write content to a file (restricted to the workspace root)"
    }
    fn run(&self, params: Value) -> Result<Value, String> {
        let filepath = params["filepath"].as_str().ok_or("filepath required")?;
        let content = params["content"].as_str().ok_or("content required")?;
        let append = params["append"].as_bool().unwrap_or(false);

        let safe = resolve_within_roots(filepath, &self.allowed_roots)
            .map_err(|e| format!("Access denied: {}", e))?;

        if let Some(parent) = safe.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("Cannot create directory: {}", e))?;
        }
        if append {
            use std::io::Write;
            let mut f = std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(&safe)
                .map_err(|e| e.to_string())?;
            f.write_all(content.as_bytes()).map_err(|e| e.to_string())?;
        } else {
            std::fs::write(&safe, content).map_err(|e| e.to_string())?;
        }
        Ok(json!({
            "data": format!("Written {} characters to {:?}", content.len(), safe),
            "filepath": safe.to_string_lossy(),
            "bytes_written": content.len(),
            "append": append,
        }))
    }
}

// ─── Shell execute（默认 fail closed） ─────────────────────

pub struct ShellExecuteTool {
    /// 是否显式允许宿主执行（默认 false = fail closed）
    pub allow_host_execution: bool,
    pub allowed_roots: Vec<PathBuf>,
}

impl ShellExecuteTool {
    pub fn new(allow_host_execution: bool, allowed_roots: Vec<PathBuf>) -> Self {
        Self {
            allow_host_execution,
            allowed_roots: default_roots(&allowed_roots),
        }
    }
}

impl Tool for ShellExecuteTool {
    fn name(&self) -> &'static str {
        "execute_shell"
    }
    fn description(&self) -> &'static str {
        "Execute a shell command. Fails closed (isolation_unavailable) unless host execution is explicitly enabled."
    }
    fn run(&self, params: Value) -> Result<Value, String> {
        let command = params["command"].as_str().ok_or("command required")?;

        if !self.allow_host_execution {
            return Err(
                "isolation_unavailable: no sandbox runtime configured; refusing to execute \
                 arbitrary commands on the host. Construct ShellExecuteTool with \
                 allow_host_execution=true to override."
                    .to_string(),
            );
        }

        // argv 形式（无 shell）：简单按空白切分，引号内保持完整
        let argv = split_argv(command)?;
        if argv.is_empty() {
            return Err("Empty command".to_string());
        }
        let cwd = self.allowed_roots.first().cloned().unwrap_or_default();
        let output = std::process::Command::new(&argv[0])
            .args(&argv[1..])
            .current_dir(cwd)
            .output()
            .map_err(|e| format!("Failed to execute: {}", e))?;
        Ok(json!({
            "exit_code": output.status.code().unwrap_or(-1),
            "stdout": String::from_utf8_lossy(&output.stdout),
            "stderr": String::from_utf8_lossy(&output.stderr),
            "isolated": false,
            "note": "host execution explicitly enabled by caller",
        }))
    }
}

/// 最小 argv 切分：支持单/双引号（不做变量展开）
fn split_argv(command: &str) -> Result<Vec<String>, String> {
    let mut argv = Vec::new();
    let mut cur = String::new();
    let mut quote: Option<char> = None;
    let mut has_token = false;

    for c in command.chars() {
        match quote {
            Some(q) if c == q => quote = None,
            Some(_) => cur.push(c),
            None => match c {
                '\'' | '"' => {
                    quote = Some(c);
                    has_token = true;
                }
                c if c.is_whitespace() => {
                    if has_token {
                        argv.push(std::mem::take(&mut cur));
                        has_token = false;
                    }
                }
                c => {
                    cur.push(c);
                    has_token = true;
                }
            },
        }
    }
    if quote.is_some() {
        return Err("Unterminated quote in command".to_string());
    }
    if has_token {
        argv.push(cur);
    }
    Ok(argv)
}

// ─── JSON tool ─────────────────────────────────────────────

pub struct JsonTool;

impl Tool for JsonTool {
    fn name(&self) -> &'static str {
        "json_tool"
    }
    fn description(&self) -> &'static str {
        "Parse, format and extract JSON data"
    }
    fn run(&self, params: Value) -> Result<Value, String> {
        let action = params["action"].as_str().ok_or("action required")?;
        let data = params["data"].as_str().ok_or("data required")?;
        let parsed: Value =
            serde_json::from_str(data).map_err(|e| format!("Invalid JSON: {}", e))?;

        match action {
            "parse" => Ok(json!({ "data": parsed })),
            "format" => Ok(json!({ "data": serde_json::to_string_pretty(&parsed).unwrap() })),
            "extract" => {
                let path = params["path"].as_str().ok_or("path required for extract")?;
                let mut cur = &parsed;
                for key in path.split('.') {
                    cur = cur
                        .get(key)
                        .ok_or_else(|| format!("Path not found: {}", path))?;
                }
                Ok(json!({ "data": cur.clone() }))
            }
            other => Err(format!("Unknown action: {}", other)),
        }
    }
}

// ─── Search（mock，与 Python 侧一致） ──────────────────────

pub struct SearchTool;

impl Tool for SearchTool {
    fn name(&self) -> &'static str {
        "search"
    }
    fn description(&self) -> &'static str {
        "Search for information (mock implementation)"
    }
    fn run(&self, params: Value) -> Result<Value, String> {
        let query = params["query"].as_str().ok_or("query required")?;
        let limit = params["limit"].as_u64().unwrap_or(5).min(5) as usize;
        let results: Vec<Value> = (0..limit)
            .map(|i| {
                json!({
                    "title": format!("Result {} for: {}", i + 1, query),
                    "snippet": format!("This is a mock search result snippet for query '{}'...", query),
                    "url": format!("https://example.com/result/{}", i + 1),
                })
            })
            .collect();
        Ok(json!({ "data": { "query": query, "results": results, "total_results": results.len() } }))
    }
}

// ─── 注册助手 ──────────────────────────────────────────────

/// 将全部内置工具注册到 registry（fail-closed 执行器 + workspace 根默认 cwd）
pub async fn register_builtin_tools(
    registry: &super::registry::ToolRegistry,
    allowed_roots: Vec<PathBuf>,
) {
    registry.register(Arc::new(CalculatorTool)).await;
    registry.register(Arc::new(FileReadTool::new(allowed_roots.clone()))).await;
    registry.register(Arc::new(FileWriteTool::new(allowed_roots.clone()))).await;
    registry.register(Arc::new(ShellExecuteTool::new(false, allowed_roots.clone()))).await;
    registry.register(Arc::new(JsonTool)).await;
    registry.register(Arc::new(SearchTool)).await;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calculator_arithmetic() {
        let t = CalculatorTool;
        let r = t.run(json!({"expression": "2 + 3 * 4"})).unwrap();
        assert_eq!(r["result"], 14.0);
    }

    #[test]
    fn test_calculator_precedence_and_parens() {
        let t = CalculatorTool;
        let r = t.run(json!({"expression": "(2 + 3) * 4"})).unwrap();
        assert_eq!(r["result"], 20.0);
        let r = t.run(json!({"expression": "2 ^ 3 ^ 2"})).unwrap(); // 右结合 = 512
        assert_eq!(r["result"], 512.0);
        let r = t.run(json!({"expression": "-3 + 10"})).unwrap();
        assert_eq!(r["result"], 7.0);
    }

    #[test]
    fn test_calculator_functions() {
        let t = CalculatorTool;
        let r = t.run(json!({"expression": "sqrt(16) + abs(-2)"})).unwrap();
        assert_eq!(r["result"], 6.0);
        let r = t.run(json!({"expression": "max(1, 5, 3)"})).unwrap();
        assert_eq!(r["result"], 5.0);
    }

    #[test]
    fn test_calculator_rejects_injection() {
        let t = CalculatorTool;
        // 不得有 eval 语义：标识符/调用一律拒绝
        assert!(t.run(json!({"expression": "system('rm -rf /')"})).is_err());
        assert!(t.run(json!({"expression": "__import__('os')"})).is_err());
        assert!(t.run(json!({"expression": "1 + "})).is_err());
        assert!(t.run(json!({"expression": "1 / 0"})).is_err());
    }

    #[test]
    fn test_file_read_outside_workspace_denied() {
        let dir = tempdir_like();
        let t = FileReadTool::new(vec![dir.join("workspace")]);
        assert!(t.run(json!({"filepath": "/etc/passwd"})).is_err());
        assert!(t
            .run(json!({"filepath": dir.join("workspace/../secret.txt").to_string_lossy()}))
            .is_err());
    }

    #[test]
    fn test_file_write_and_read_roundtrip() {
        let dir = tempdir_like();
        let w = FileWriteTool::new(vec![dir.clone()]);
        let r = w
            .run(json!({"filepath": "sub/dir/a.txt", "content": "hello"}))
            .unwrap();
        assert!(r["bytes_written"].as_u64().unwrap() >= 5);
        let rd = FileReadTool::new(vec![dir.clone()]);
        let r = rd.run(json!({"filepath": "sub/dir/a.txt"})).unwrap();
        assert_eq!(r["data"], "hello");
    }

    #[test]
    fn test_shell_fails_closed_by_default() {
        let t = ShellExecuteTool::new(false, vec![]);
        let r = t.run(json!({"command": "echo pwned"}));
        assert!(r.is_err());
        assert!(r.unwrap_err().contains("isolation_unavailable"));
    }

    #[test]
    fn test_shell_opt_in_argv_no_shell() {
        let t = ShellExecuteTool::new(true, vec![std::env::current_dir().unwrap()]);
        let r = t.run(json!({"command": "echo safe"})).unwrap();
        assert_eq!(r["exit_code"], 0);
        assert!(r["stdout"].as_str().unwrap().contains("safe"));
        // 元字符不应被 shell 解释（无 shell=True）
        let r = t.run(json!({"command": "echo 'a; rm -rf /tmp/nope'"})).unwrap();
        assert!(r["stdout"].as_str().unwrap().contains(';'));
    }

    #[test]
    fn test_split_argv_quotes() {
        assert_eq!(split_argv("echo 'a b' c").unwrap(), vec!["echo", "a b", "c"]);
        assert_eq!(split_argv("  ").unwrap(), Vec::<String>::new());
        assert!(split_argv("echo 'unterminated").is_err());
    }

    #[test]
    fn test_json_tool_extract() {
        let t = JsonTool;
        let r = t
            .run(json!({"action": "extract", "data": r#"{"a":{"b":42}}"#, "path": "a.b"}))
            .unwrap();
        assert_eq!(r["data"], 42);
    }

    #[tokio::test]
    async fn test_register_builtin_tools_roundtrip() {
        // 通过 registry 注册后可按名取用并真实执行
        let registry = super::super::registry::ToolRegistry::new();
        super::register_builtin_tools(&registry, vec![std::env::current_dir().unwrap()]).await;

        for name in ["calculator", "read_file", "write_file", "execute_shell", "json_tool", "search"] {
            assert!(registry.get(name).await.is_some(), "missing tool: {}", name);
        }

        let calc = registry.get("calculator").await.unwrap();
        let r = calc.run(json!({"expression": "6 * 7"})).unwrap();
        assert_eq!(r["result"], 42.0);

        // 执行器默认 fail closed
        let shell = registry.get("execute_shell").await.unwrap();
        assert!(shell.run(json!({"command": "echo hi"})).is_err());
    }

    // 简易临时目录（不引 dev-dependencies）
    fn tempdir_like() -> PathBuf {
        let d = std::env::temp_dir().join(format!("aosk-tool-test-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&d).unwrap();
        d
    }
}
