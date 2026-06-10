use bitween_payroll_api::{PlatformLiveConfig, build_platform_live_view};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let view = build_platform_live_view(PlatformLiveConfig::from_env());
    println!("{}", serde_json::to_string_pretty(&view)?);
    Ok(())
}
