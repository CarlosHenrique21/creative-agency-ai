from google.adk.apps import App, ResumabilityConfig

from core.orchestrator import agency_pipeline

# Exportar App com resumability_config habilita LongRunningFunctionTool pausar o pipeline
root_agent = App(
    name="social_media_agency",
    root_agent=agency_pipeline,
    resumability_config=ResumabilityConfig(is_resumable=True),
)
