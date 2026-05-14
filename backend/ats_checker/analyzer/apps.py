# analyzer/apps.py
from django.apps import AppConfig

class AnalyzerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analyzer'

    def ready(self):
        try:
            # FIX: Changed ATSInference -> ATSMLPredictor to match ml_predictor.py
            from .ml_engine.ml_predictor import ATSMLPredictor
            self.ats_engine = ATSMLPredictor()
            print("ATS ML Engine loaded successfully")
        except FileNotFoundError as e:
            print(f" {e}")
        except Exception as e:
            print(f" Failed to load ML engine: {e}")