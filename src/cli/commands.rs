// 命令行命令定义
use clap::Subcommand;

#[derive(Debug, Subcommand)]
pub enum Commands {
    /// 启动内核
    Start,
    /// 停止内核
    Stop,
    /// 列出进程
    Ps,
    /// 显示状态
    Status,
}
