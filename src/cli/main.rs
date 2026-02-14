// 命令行入口点
use clap::Parser;

use super::commands::Commands;

#[derive(Debug, Parser)]
#[clap(name = "agent-os-kernel")]
#[clap(about = "AI Agent 操作系统内核")]
pub struct Cli {
    #[clap(subcommand)]
    command: Commands,
}

pub async fn run() {
    let cli = Cli::parse();

    match &cli.command {
        Commands::Start => println!("启动内核"),
        Commands::Stop => println!("停止内核"),
        Commands::Ps => println!("列出进程"),
        Commands::Status => println!("显示状态"),
    }
}
