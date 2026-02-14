//! 指标收集器模块
//!
//! 提供基本的指标收集功能，支持计数器和 Gauge

use std::collections::HashMap;

/// 指标收集器
///
/// 用于收集和查询运行时指标
pub struct MetricsCollector {
    counters: HashMap<String, u64>,
    gauges: HashMap<String, f64>,
}

impl MetricsCollector {
    /// 创建新的指标收集器
    pub fn new() -> Self {
        Self {
            counters: HashMap::new(),
            gauges: HashMap::new(),
        }
    }

    /// 增加计数器值
    pub fn increment_counter(&mut self, name: &str, value: u64) {
        let entry = self.counters.entry(name.to_string()).or_insert(0);
        *entry += value;
    }

    /// 设置 Gauge 值
    pub fn set_gauge(&mut self, name: &str, value: f64) {
        self.gauges.insert(name.to_string(), value);
    }

    /// 获取计数器值
    pub fn get_counter(&self, name: &str) -> Option<u64> {
        self.counters.get(name).copied()
    }

    /// 获取 Gauge 值
    pub fn get_gauge(&self, name: &str) -> Option<f64> {
        self.gauges.get(name).copied()
    }
}
