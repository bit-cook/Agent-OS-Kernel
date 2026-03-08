// 命令行入口点
use clap::Parser;

#[derive(Debug, Parser)]
#[clap(name = "agent-os-kernel")]
#[clap(about = "AI Agent 操作系统内核")]
struct Cli {
    #[clap(subcommand)]
    command: Commands,
}

#[derive(Debug, clap::Subcommand)]
enum Commands {
    /// 启动内核
    Start,
    /// 停止内核
    Stop,
    /// 列出进程
    Ps,
    /// 显示状态
    Status,
    /// 启动 Web API 服务器
    Serve {
        /// 监听端口
        #[clap(long, default_value = "9090")]
        port: u16,
    },
}

#[tokio::main]
async fn main() {
    env_logger::init();
    let cli = Cli::parse();

    match cli.command {
        Commands::Start => println!("🚀 启动 Agent OS Kernel..."),
        Commands::Stop => println!("⏹️ 停止内核..."),
        Commands::Ps => println!("📋 进程列表"),
        Commands::Status => println!("✅ 运行中"),
        Commands::Serve { port } => {
            println!("🚀 启动 Web API 服务器...");
            if let Err(e) = agent_os_kernel::api::server::start_server(port).await {
                eprintln!("❌ 服务器启动失败: {}", e);
                std::process::exit(1);
            }
        }
    }
}
