# -*- coding: utf-8 -*-
"""
Zydus Pharma Oncology - Sensor Simulator
=========================================
High-fidelity telemetry simulator broadcasting calibrated multi-channel sensor
readings for all 20 pharma oncology assets directly to Kafka topic 'equipment.sensors.raw'.
"""

import json
import time
import random
import os
import logging
from datetime import datetime, timezone
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sensor-simulator")

EQUIPMENT_SPEC = {
    "GRAN-LINE-01": {
        "name": "High Shear Mixer Granulator 600L",
        "category": "Granulation",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 10.0,
                "max": 28.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 45.0,
                "critical": 65.0
            },
            "temperature_c": {
                "unit": "C",
                "min": 20.0,
                "max": 42.0,
                "min_phys": 0.0,
                "max_phys": 120.0,
                "warning": 60.0,
                "critical": 80.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 1.0,
                "max": 2.5,
                "min_phys": 0.0,
                "max_phys": 10.0,
                "warning": 4.0,
                "critical": 6.0
            },
            "current_draw_a": {
                "unit": "A",
                "min": 15.0,
                "max": 35.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 55.0,
                "critical": 75.0
            },
            "motor_rpm": {
                "unit": "RPM",
                "min": 800.0,
                "max": 1500.0,
                "min_phys": 0.0,
                "max_phys": 3000.0,
                "warning": 1900.0,
                "critical": 2400.0
            }
        }
    },
    "FBD-DRYER-01": {
        "name": "Fluid Bed Dryer FBD-300",
        "category": "Granulation",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 5.0,
                "max": 20.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 35.0,
                "critical": 55.0
            },
            "temperature_c": {
                "unit": "C",
                "min": 40.0,
                "max": 75.0,
                "min_phys": 0.0,
                "max_phys": 120.0,
                "warning": 90.0,
                "critical": 105.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 0.2,
                "max": 0.8,
                "min_phys": 0.0,
                "max_phys": 10.0,
                "warning": 1.5,
                "critical": 2.5
            },
            "current_draw_a": {
                "unit": "A",
                "min": 10.0,
                "max": 25.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 40.0,
                "critical": 60.0
            },
            "flow_rate_lpm": {
                "unit": "L/min",
                "min": 150.0,
                "max": 350.0,
                "min_phys": 0.0,
                "max_phys": 500.0,
                "warning": 420.0,
                "critical": 480.0
            }
        }
    },
    "TAB-PRESS-01": {
        "name": "Rotary Tablet Press 45-Station",
        "category": "Granulation",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 15.0,
                "max": 32.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 50.0,
                "critical": 70.0
            },
            "temperature_c": {
                "unit": "C",
                "min": 22.0,
                "max": 40.0,
                "min_phys": 0.0,
                "max_phys": 120.0,
                "warning": 58.0,
                "critical": 75.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 2.0,
                "max": 5.0,
                "min_phys": 0.0,
                "max_phys": 10.0,
                "warning": 7.0,
                "critical": 9.0
            },
            "current_draw_a": {
                "unit": "A",
                "min": 20.0,
                "max": 45.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 65.0,
                "critical": 85.0
            },
            "motor_rpm": {
                "unit": "RPM",
                "min": 1200.0,
                "max": 2200.0,
                "min_phys": 0.0,
                "max_phys": 3000.0,
                "warning": 2600.0,
                "critical": 2900.0
            }
        }
    },
    "COATER-01": {
        "name": "Auto-Coater Perforated Pan 150kg",
        "category": "Granulation",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 8.0,
                "max": 22.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 38.0,
                "critical": 58.0
            },
            "temperature_c": {
                "unit": "C",
                "min": 35.0,
                "max": 65.0,
                "min_phys": 0.0,
                "max_phys": 120.0,
                "warning": 80.0,
                "critical": 98.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 1.0,
                "max": 3.0,
                "min_phys": 0.0,
                "max_phys": 10.0,
                "warning": 4.5,
                "critical": 6.5
            },
            "current_draw_a": {
                "unit": "A",
                "min": 12.0,
                "max": 28.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 42.0,
                "critical": 62.0
            },
            "motor_rpm": {
                "unit": "RPM",
                "min": 300.0,
                "max": 800.0,
                "min_phys": 0.0,
                "max_phys": 3000.0,
                "warning": 1100.0,
                "critical": 1400.0
            }
        }
    },
    "VIAL-FILL-01": {
        "name": "Aseptic Vial Filling & Stoppering Line",
        "category": "Sterile Injectables",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 5.0,
                "max": 18.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 30.0,
                "critical": 48.0
            },
            "temperature_c": {
                "unit": "C",
                "min": 18.0,
                "max": 26.0,
                "min_phys": 0.0,
                "max_phys": 120.0,
                "warning": 35.0,
                "critical": 50.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 0.1,
                "max": 0.5,
                "min_phys": 0.0,
                "max_phys": 10.0,
                "warning": 1.0,
                "critical": 2.0
            },
            "current_draw_a": {
                "unit": "A",
                "min": 8.0,
                "max": 20.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 32.0,
                "critical": 48.0
            },
            "pulse_count": {
                "unit": "count",
                "min": 5000.0,
                "max": 40000.0,
                "min_phys": 0.0,
                "max_phys": 100000.0,
                "warning": 60000.0,
                "critical": 85000.0
            }
        }
    },
    "LYO-CHAMBER-01": {
        "name": "Industrial Freeze Dryer Lyophilizer 50m2",
        "category": "Sterile Injectables",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 8.0,
                "max": 24.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 40.0,
                "critical": 60.0
            },
            "temperature_c": {
                "unit": "C",
                "min": -55.0,
                "max": 25.0,
                "min_phys": -80.0,
                "max_phys": 80.0,
                "warning": 45.0,
                "critical": 65.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 0.001,
                "max": 0.1,
                "min_phys": 0.0,
                "max_phys": 5.0,
                "warning": 0.5,
                "critical": 1.5
            },
            "current_draw_a": {
                "unit": "A",
                "min": 25.0,
                "max": 60.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 80.0,
                "critical": 95.0
            },
            "flow_rate_lpm": {
                "unit": "L/min",
                "min": 50.0,
                "max": 200.0,
                "min_phys": 0.0,
                "max_phys": 500.0,
                "warning": 280.0,
                "critical": 360.0
            }
        }
    },
    "AUTOCLAVE-01": {
        "name": "Porous Load Steam Sterilizer 2000L",
        "category": "Sterile Injectables",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 4.0,
                "max": 15.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 28.0,
                "critical": 45.0
            },
            "temperature_c": {
                "unit": "C",
                "min": 115.0,
                "max": 124.0,
                "min_phys": 0.0,
                "max_phys": 150.0,
                "warning": 132.0,
                "critical": 142.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 1.8,
                "max": 2.6,
                "min_phys": 0.0,
                "max_phys": 10.0,
                "warning": 3.2,
                "critical": 4.0
            },
            "current_draw_a": {
                "unit": "A",
                "min": 15.0,
                "max": 35.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 50.0,
                "critical": 70.0
            },
            "flow_rate_lpm": {
                "unit": "L/min",
                "min": 80.0,
                "max": 220.0,
                "min_phys": 0.0,
                "max_phys": 500.0,
                "warning": 300.0,
                "critical": 400.0
            }
        }
    },
    "WFI-STILL-01": {
        "name": "Multiple Effect WFI Generation Still",
        "category": "Sterile Injectables",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 6.0,
                "max": 20.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 34.0,
                "critical": 52.0
            },
            "temperature_c": {
                "unit": "C",
                "min": 120.0,
                "max": 160.0,
                "min_phys": 0.0,
                "max_phys": 180.0,
                "warning": 170.0,
                "critical": 180.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 3.0,
                "max": 5.5,
                "min_phys": 0.0,
                "max_phys": 10.0,
                "warning": 7.0,
                "critical": 8.5
            },
            "current_draw_a": {
                "unit": "A",
                "min": 20.0,
                "max": 45.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 65.0,
                "critical": 85.0
            },
            "flow_rate_lpm": {
                "unit": "L/min",
                "min": 100.0,
                "max": 300.0,
                "min_phys": 0.0,
                "max_phys": 500.0,
                "warning": 380.0,
                "critical": 460.0
            }
        }
    },
    "BIOREACTOR-01": {
        "name": "Single-Use Bioreactor 2000L",
        "category": "Bioprocessing",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 5.0,
                "max": 18.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 32.0,
                "critical": 50.0
            },
            "temperature_c": {
                "unit": "C",
                "min": 35.0,
                "max": 38.0,
                "min_phys": 0.0,
                "max_phys": 120.0,
                "warning": 42.0,
                "critical": 50.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 0.05,
                "max": 0.3,
                "min_phys": 0.0,
                "max_phys": 10.0,
                "warning": 0.8,
                "critical": 1.5
            },
            "current_draw_a": {
                "unit": "A",
                "min": 8.0,
                "max": 22.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 35.0,
                "critical": 52.0
            },
            "motor_rpm": {
                "unit": "RPM",
                "min": 40.0,
                "max": 250.0,
                "min_phys": 0.0,
                "max_phys": 3000.0,
                "warning": 350.0,
                "critical": 500.0
            }
        }
    },
    "TFF-SKID-01": {
        "name": "Tangential Flow Filtration Skid",
        "category": "Bioprocessing",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 10.0,
                "max": 26.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 42.0,
                "critical": 62.0
            },
            "temperature_c": {
                "unit": "C",
                "min": 4.0,
                "max": 22.0,
                "min_phys": 0.0,
                "max_phys": 120.0,
                "warning": 30.0,
                "critical": 45.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 1.5,
                "max": 3.5,
                "min_phys": 0.0,
                "max_phys": 10.0,
                "warning": 5.0,
                "critical": 7.0
            },
            "current_draw_a": {
                "unit": "A",
                "min": 12.0,
                "max": 30.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 45.0,
                "critical": 65.0
            },
            "flow_rate_lpm": {
                "unit": "L/min",
                "min": 40.0,
                "max": 150.0,
                "min_phys": 0.0,
                "max_phys": 500.0,
                "warning": 210.0,
                "critical": 280.0
            }
        }
    },
    "CHROM-SKID-01": {
        "name": "Preparative Chromatography Skid",
        "category": "Bioprocessing",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 8.0,
                "max": 22.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 36.0,
                "critical": 54.0
            },
            "temperature_c": {
                "unit": "C",
                "min": 4.0,
                "max": 18.0,
                "min_phys": 0.0,
                "max_phys": 120.0,
                "warning": 26.0,
                "critical": 38.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 2.0,
                "max": 4.5,
                "min_phys": 0.0,
                "max_phys": 10.0,
                "warning": 6.0,
                "critical": 8.0
            },
            "current_draw_a": {
                "unit": "A",
                "min": 10.0,
                "max": 28.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 42.0,
                "critical": 60.0
            },
            "flow_rate_lpm": {
                "unit": "L/min",
                "min": 20.0,
                "max": 120.0,
                "min_phys": 0.0,
                "max_phys": 500.0,
                "warning": 170.0,
                "critical": 230.0
            }
        }
    },
    "CIP-SYSTEM-01": {
        "name": "Clean-In-Place Recirculation Unit",
        "category": "Bioprocessing",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 12.0,
                "max": 30.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 48.0,
                "critical": 68.0
            },
            "temperature_c": {
                "unit": "C",
                "min": 60.0,
                "max": 85.0,
                "min_phys": 0.0,
                "max_phys": 120.0,
                "warning": 95.0,
                "critical": 110.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 2.5,
                "max": 4.8,
                "min_phys": 0.0,
                "max_phys": 10.0,
                "warning": 6.2,
                "critical": 8.0
            },
            "current_draw_a": {
                "unit": "A",
                "min": 18.0,
                "max": 40.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 58.0,
                "critical": 78.0
            },
            "flow_rate_lpm": {
                "unit": "L/min",
                "min": 150.0,
                "max": 350.0,
                "min_phys": 0.0,
                "max_phys": 500.0,
                "warning": 420.0,
                "critical": 480.0
            }
        }
    },
    "HPLC-AUTO-01": {
        "name": "UPLC Quaternary Solvent Pump",
        "category": "Analytical Lab",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 2.0,
                "max": 10.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 18.0,
                "critical": 30.0
            },
            "temperature_c": {
                "unit": "C",
                "min": 18.0,
                "max": 30.0,
                "min_phys": 0.0,
                "max_phys": 120.0,
                "warning": 42.0,
                "critical": 55.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 200.0,
                "max": 600.0,
                "min_phys": 0.0,
                "max_phys": 1000.0,
                "warning": 750.0,
                "critical": 900.0
            },
            "current_draw_a": {
                "unit": "A",
                "min": 2.0,
                "max": 8.0,
                "min_phys": 0.0,
                "max_phys": 50.0,
                "warning": 14.0,
                "critical": 22.0
            },
            "flow_rate_lpm": {
                "unit": "L/min",
                "min": 0.2,
                "max": 1.5,
                "min_phys": 0.0,
                "max_phys": 10.0,
                "warning": 2.5,
                "critical": 4.0
            }
        }
    },
    "LCMS-CHAMBER-01": {
        "name": "LC-MS/MS Triple Quadrupole Chamber",
        "category": "Analytical Lab",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 1.0,
                "max": 8.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 15.0,
                "critical": 25.0
            },
            "temperature_c": {
                "unit": "C",
                "min": 150.0,
                "max": 280.0,
                "min_phys": 0.0,
                "max_phys": 350.0,
                "warning": 310.0,
                "critical": 340.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 0.0001,
                "max": 0.01,
                "min_phys": 0.0,
                "max_phys": 5.0,
                "warning": 0.05,
                "critical": 0.2
            },
            "current_draw_a": {
                "unit": "A",
                "min": 8.0,
                "max": 22.0,
                "min_phys": 0.0,
                "max_phys": 50.0,
                "warning": 32.0,
                "critical": 44.0
            },
            "flow_rate_lpm": {
                "unit": "L/min",
                "min": 2.0,
                "max": 12.0,
                "min_phys": 0.0,
                "max_phys": 50.0,
                "warning": 18.0,
                "critical": 26.0
            }
        }
    },
    "SPECTRO-UV-01": {
        "name": "UV-Vis Double Beam Spectrophotometer",
        "category": "Analytical Lab",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 0.5,
                "max": 5.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 10.0,
                "critical": 18.0
            },
            "temperature_c": {
                "unit": "C",
                "min": 18.0,
                "max": 28.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 38.0,
                "critical": 48.0
            },
            "current_draw_a": {
                "unit": "A",
                "min": 1.0,
                "max": 4.5,
                "min_phys": 0.0,
                "max_phys": 20.0,
                "warning": 7.0,
                "critical": 10.0
            },
            "optical_transmittance": {
                "unit": "%",
                "min": 85.0,
                "max": 99.5,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 75.0,
                "critical": 60.0
            },
            "pulse_count": {
                "unit": "count",
                "min": 1000.0,
                "max": 20000.0,
                "min_phys": 0.0,
                "max_phys": 50000.0,
                "warning": 30000.0,
                "critical": 42000.0
            }
        }
    },
    "DISSOLUTION-01": {
        "name": "Automated USP Dissolution Tester",
        "category": "Analytical Lab",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 2.0,
                "max": 8.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 16.0,
                "critical": 26.0
            },
            "temperature_c": {
                "unit": "C",
                "min": 36.5,
                "max": 37.5,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 39.0,
                "critical": 42.0
            },
            "current_draw_a": {
                "unit": "A",
                "min": 3.0,
                "max": 9.0,
                "min_phys": 0.0,
                "max_phys": 30.0,
                "warning": 14.0,
                "critical": 20.0
            },
            "motor_rpm": {
                "unit": "RPM",
                "min": 48.0,
                "max": 102.0,
                "min_phys": 0.0,
                "max_phys": 500.0,
                "warning": 120.0,
                "critical": 150.0
            },
            "flow_rate_lpm": {
                "unit": "L/min",
                "min": 0.5,
                "max": 2.5,
                "min_phys": 0.0,
                "max_phys": 20.0,
                "warning": 4.0,
                "critical": 6.0
            }
        }
    },
    "LINAC-01": {
        "name": "Varian TrueBeam Linear Accelerator",
        "category": "Hospital Oncology",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 4.0,
                "max": 16.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 28.0,
                "critical": 46.0
            },
            "temperature_c": {
                "unit": "C",
                "min": 20.0,
                "max": 32.0,
                "min_phys": 0.0,
                "max_phys": 120.0,
                "warning": 42.0,
                "critical": 55.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 2.5,
                "max": 4.2,
                "min_phys": 0.0,
                "max_phys": 10.0,
                "warning": 5.5,
                "critical": 7.0
            },
            "current_draw_a": {
                "unit": "A",
                "min": 20.0,
                "max": 55.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 75.0,
                "critical": 92.0
            },
            "beam_current_ma": {
                "unit": "mA",
                "min": 50.0,
                "max": 220.0,
                "min_phys": 0.0,
                "max_phys": 500.0,
                "warning": 280.0,
                "critical": 360.0
            }
        }
    },
    "CYCLOTRON-01": {
        "name": "Medical PET Radioisotope Cyclotron",
        "category": "Hospital Oncology",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 8.0,
                "max": 22.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 38.0,
                "critical": 56.0
            },
            "temperature_c": {
                "unit": "C",
                "min": -20.0,
                "max": 25.0,
                "min_phys": -50.0,
                "max_phys": 100.0,
                "warning": 40.0,
                "critical": 58.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 0.0001,
                "max": 0.05,
                "min_phys": 0.0,
                "max_phys": 10.0,
                "warning": 0.2,
                "critical": 1.0
            },
            "current_draw_a": {
                "unit": "A",
                "min": 40.0,
                "max": 95.0,
                "min_phys": 0.0,
                "max_phys": 150.0,
                "warning": 120.0,
                "critical": 140.0
            },
            "flow_rate_lpm": {
                "unit": "L/min",
                "min": 100.0,
                "max": 280.0,
                "min_phys": 0.0,
                "max_phys": 500.0,
                "warning": 350.0,
                "critical": 420.0
            }
        }
    },
    "MRI-CRYO-01": {
        "name": "3T MRI Superconducting Cryocooler",
        "category": "Hospital Oncology",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 10.0,
                "max": 25.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 40.0,
                "critical": 60.0
            },
            "temperature_c": {
                "unit": "C",
                "min": -269.0,
                "max": -265.0,
                "min_phys": -273.0,
                "max_phys": 50.0,
                "warning": -255.0,
                "critical": -240.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 14.0,
                "max": 19.0,
                "min_phys": 0.0,
                "max_phys": 30.0,
                "warning": 22.5,
                "critical": 26.0
            },
            "current_draw_a": {
                "unit": "A",
                "min": 15.0,
                "max": 35.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 50.0,
                "critical": 70.0
            },
            "flow_rate_lpm": {
                "unit": "L/min",
                "min": 20.0,
                "max": 65.0,
                "min_phys": 0.0,
                "max_phys": 200.0,
                "warning": 85.0,
                "critical": 110.0
            }
        }
    },
    "ULT-FREEZER-01": {
        "name": "-80C Cryopreservation Biobank Vault",
        "category": "Hospital Oncology",
        "sensors": {
            "vibration_hz": {
                "unit": "Hz",
                "min": 4.0,
                "max": 16.0,
                "min_phys": 0.0,
                "max_phys": 100.0,
                "warning": 28.0,
                "critical": 45.0
            },
            "temperature_c": {
                "unit": "C",
                "min": -86.0,
                "max": -78.0,
                "min_phys": -100.0,
                "max_phys": 50.0,
                "warning": -68.0,
                "critical": -55.0
            },
            "pressure_bar": {
                "unit": "bar",
                "min": 10.0,
                "max": 16.0,
                "min_phys": 0.0,
                "max_phys": 25.0,
                "warning": 19.5,
                "critical": 23.0
            },
            "current_draw_a": {
                "unit": "A",
                "min": 6.0,
                "max": 18.0,
                "min_phys": 0.0,
                "max_phys": 50.0,
                "warning": 26.0,
                "critical": 38.0
            },
            "door_open_sec": {
                "unit": "sec",
                "min": 0.0,
                "max": 30.0,
                "min_phys": 0.0,
                "max_phys": 600.0,
                "warning": 90.0,
                "critical": 180.0
            }
        }
    }
}

class SensorSimulator:
    def __init__(self):
        self.kafka_broker = os.environ.get("KAFKA_BROKER", "localhost:9092")
        self.topic = "equipment.sensors.raw"
        self.producer = None
        self.anomaly_states = {}
        self._connect_kafka()

    def _connect_kafka(self):
        while True:
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=self.kafka_broker,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    acks="all",
                    retries=3,
                )
                logger.info("Connected to Kafka broker at %s", self.kafka_broker)
                return
            except NoBrokersAvailable:
                logger.warning("Kafka broker not available at %s. Retrying in 4s...", self.kafka_broker)
                time.sleep(4)
            except Exception as e:
                logger.error("Kafka connection error: %s. Retrying in 4s...", e)
                time.sleep(4)

    def _generate_value(self, eq_id, s_name, s_info):
        key = f"{eq_id}:{s_name}"
        if key not in self.anomaly_states:
            self.anomaly_states[key] = {
                "in_anomaly": False,
                "duration": 0,
                "step": 0,
                "offset": 0.0,
            }
        st = self.anomaly_states[key]

        # 3% chance of entering transient anomaly state
        if not st["in_anomaly"] and random.random() < 0.03:
            st["in_anomaly"] = True
            st["duration"] = random.randint(5, 15)
            st["step"] = 0
            st["offset"] = 0.0

        nom_min = s_info["min"]
        nom_max = s_info["max"]
        mid = (nom_min + nom_max) / 2.0
        span = (nom_max - nom_min) / 2.0
        base = random.gauss(mid, span * 0.2)
        base = max(nom_min * 0.95, min(nom_max * 1.05, base))
        is_anomaly = False

        if st["in_anomaly"]:
            is_anomaly = True
            st["step"] += 1
            st["offset"] += (s_info["warning"] - nom_max) * 0.15
            val = base + st["offset"]
            if st["step"] >= st["duration"]:
                st["in_anomaly"] = False
                st["offset"] = 0.0
        else:
            val = base

        val = max(s_info["min_phys"], min(s_info["max_phys"], val))
        return round(val, 2), is_anomaly

    def run(self):
        total_sensors = sum(len(e["sensors"]) for e in EQUIPMENT_SPEC.values())
        logger.info("Starting Zydus Sensor Simulator")
        logger.info("  Equipment: %s assets", len(EQUIPMENT_SPEC))
        logger.info("  Sensors:   %s telemetry streams", total_sensors)
        logger.info("  Interval:  5 seconds")
        logger.info("  Topic:     %s", self.topic)

        cycle = 0
        while True:
            cycle += 1
            count = 0
            anomaly_count = 0
            ts = datetime.now(timezone.utc).isoformat()

            for eq_id, eq_info in EQUIPMENT_SPEC.items():
                for s_name, s_info in eq_info["sensors"].items():
                    val, is_anom = self._generate_value(eq_id, s_name, s_info)
                    payload = {
                        "equipment_id": eq_id,
                        "equipment_type": eq_info["category"],
                        "sensor_name": s_name,
                        "value": val,
                        "unit": s_info["unit"],
                        "timestamp": ts,
                        "is_anomaly": is_anom,
                    }
                    try:
                        self.producer.send(self.topic, value=payload)
                    except Exception as e:
                        logger.error("Failed to send payload: %s", e)
                        self._connect_kafka()
                        self.producer.send(self.topic, value=payload)

                    count += 1
                    if is_anom:
                        anomaly_count += 1

            self.producer.flush()
            logger.info("[Cycle %s] Published %s readings (%s anomalies) for %s assets", cycle, count, anomaly_count, len(EQUIPMENT_SPEC))
            time.sleep(5)

if __name__ == "__main__":
    sim = SensorSimulator()
    sim.run()
