// 指标收集器
use std::collections::HashMap;

pub struct MetricsCollector {
    counters: HashMap<String, u64>,
    gauges: HashMap<String, f64>,
}

impl MetricsCollector {
    pub fn new() -> Self {
        Self {
            counters: HashMap::new(),
            gauges: HashMap::new(),
        }
    }

    pub fn increment_counter(&mut self, name: &str, value: u64) {
        let entry = self.counters.entry(name.to_string()).or_insert(0);
        *entry += value;
    }

    pub fn set_gauge(&mut self, name: &str, value: f64) {
        self.gauges.insert(name.to_string(), value);
    }

    pub fn get_counter(&self, name: &str) -> Option<u64> {
        self.counters.get(name).copied()
    }

    pub fn get_gauge(&self, name: &str) -> Option<f64> {
        self.gauges.get(name).copied()
    }
}
