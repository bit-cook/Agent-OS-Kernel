//! Python Binding Module using PyO3
//!
//! This module provides Python bindings for Agent-OS-Kernel
//! Run with: cargo build --lib && maturin develop

use pyo3::prelude::*;

/// Greet from Rust
#[pyfunction]
fn greet(name: Option<&str>) -> String {
    let name = name.unwrap_or("XieMate");
    format!("Hello, {}! From Rust 🦀", name)
}

/// Get kernel version
#[pyfunction]
fn kernel_version() -> String {
    "0.2.0".to_string()
}

/// Simple addition
#[pyfunction]
fn add(a: i32, b: i32) -> i32 {
    a + b
}

/// Context info
#[pyfunction]
fn get_context_info() -> PyResult<Py<PyDict>> {
    Python::with_gil(|py| {
        let dict = PyDict::new(py);
        dict.set_item("version", "0.2.0")?;
        dict.set_item("language", "Rust")?;
        dict.set_item("status", "active")?;
        Ok(dict.into())
    })
}

/// Agent info
#[pyclass]
struct AgentInfo {
    name: String,
    status: String,
}

#[pymethods]
impl AgentInfo {
    #[new]
    fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            status: "running".to_string(),
        }
    }

    #[getter]
    fn name(&self) -> &str {
        &self.name
    }

    #[getter]
    fn status(&self) -> &str {
        &self.status
    }
}

/// Python module definition
#[pymodule]
fn agent_os_kernel(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(greet, m)?)?;
    m.add_function(wrap_pyfunction!(kernel_version, m)?)?;
    m.add_function(wrap_pyfunction!(add, m)?)?;
    m.add_function(wrap_pyfunction!(get_context_info, m)?)?;
    m.add_class::<AgentInfo>()?;
    Ok(())
}
