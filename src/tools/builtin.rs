use super::base::Tool;

pub struct EchoTool;

impl Tool for EchoTool {
    fn name(&self) -> &'static str {
        "echo"
    }

    fn description(&self) -> &'static str {
        "Echo input back"
    }

    fn run(&self, params: serde_json::Value) -> Result<serde_json::Value, String> {
        Ok(params)
    }
}

pub struct CalculatorTool;

impl Tool for CalculatorTool {
    fn name(&self) -> &'static str {
        "calculator"
    }

    fn description(&self) -> &'static str {
        "Perform basic calculations"
    }

    fn run(&self, params: serde_json::Value) -> Result<serde_json::Value, String> {
        let expression = params["expression"].as_str().ok_or("Expression required")?;
        
        // Use a simple evaluator or parse as f64
        let result: f64 = expression.parse().map_err(|_: std::num::ParseFloatError| "Invalid expression".to_string())?;
        
        Ok(serde_json::json!({ "result": result }))
    }
}
