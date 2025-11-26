"""Configuration loader for demo YAML files."""
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class DemoConfig:
    """Parsed demo configuration."""
    demo_name: str
    description: str
    gazebo_world: str
    timeout: float
    models: Dict[str, Any]
    extra: Dict[str, Any]


class ConfigLoader:
    """Loads and validates demo configuration from YAML files."""

    @staticmethod
    def load_yaml(file_path: str) -> Dict[str, Any]:
        """Load YAML file.

        Args:
            file_path: Path to YAML file

        Returns:
            Parsed YAML as dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")

        with open(path, 'r') as f:
            try:
                config = yaml.safe_load(f)
                return config if config is not None else {}
            except yaml.YAMLError as e:
                raise yaml.YAMLError(f"Invalid YAML in {file_path}: {e}")

    @staticmethod
    def parse_demo_config(config_dict: Dict[str, Any]) -> DemoConfig:
        """Parse demo configuration dictionary.

        Args:
            config_dict: Dictionary from YAML

        Returns:
            DemoConfig object

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        required_fields = ['demo_name', 'description', 'gazebo_world']
        for field in required_fields:
            if field not in config_dict:
                raise ValueError(f"Missing required field in config: {field}")

        # Extract fields
        demo_name = config_dict['demo_name']
        description = config_dict['description']
        gazebo_world = config_dict['gazebo_world']
        timeout = config_dict.get('timeout', 30.0)
        models = config_dict.get('models', {})

        # Extract extra fields (everything else)
        extra = {
            k: v for k, v in config_dict.items()
            if k not in ['demo_name', 'description', 'gazebo_world', 'timeout', 'models']
        }

        return DemoConfig(
            demo_name=demo_name,
            description=description,
            gazebo_world=gazebo_world,
            timeout=timeout,
            models=models,
            extra=extra
        )

    @staticmethod
    def load_demo_config(file_path: str) -> DemoConfig:
        """Load and parse demo configuration file.

        Args:
            file_path: Path to config.yaml

        Returns:
            DemoConfig object

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is invalid
            ValueError: If required fields are missing
        """
        config_dict = ConfigLoader.load_yaml(file_path)
        return ConfigLoader.parse_demo_config(config_dict)

    @staticmethod
    def get_model_config(config: DemoConfig, model_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific model.

        Args:
            config: DemoConfig object
            model_name: Name of model

        Returns:
            Model configuration dictionary or None if not found
        """
        return config.models.get(model_name)

    @staticmethod
    def get_model_pose(config: DemoConfig, model_name: str) -> Optional[Dict[str, Any]]:
        """Get pose configuration for a specific model.

        Args:
            config: DemoConfig object
            model_name: Name of model

        Returns:
            Pose dictionary with 'position' and 'orientation' or None
        """
        model_config = ConfigLoader.get_model_config(config, model_name)
        if model_config:
            return model_config.get('pose')
        return None

    @staticmethod
    def get_model_sdf_path(config: DemoConfig, model_name: str) -> Optional[str]:
        """Get SDF file path for a specific model.

        Args:
            config: DemoConfig object
            model_name: Name of model

        Returns:
            SDF file path or None
        """
        model_config = ConfigLoader.get_model_config(config, model_name)
        if model_config:
            return model_config.get('sdf_file')
        return None

    @staticmethod
    def validate_config(config: DemoConfig) -> tuple[bool, list[str]]:
        """Validate demo configuration.

        Args:
            config: DemoConfig to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check demo_name
        if not config.demo_name or not isinstance(config.demo_name, str):
            errors.append("demo_name must be a non-empty string")

        # Check description
        if not config.description or not isinstance(config.description, str):
            errors.append("description must be a non-empty string")

        # Check gazebo_world
        if not config.gazebo_world or not isinstance(config.gazebo_world, str):
            errors.append("gazebo_world must be a non-empty string")

        # Check timeout
        if not isinstance(config.timeout, (int, float)) or config.timeout <= 0:
            errors.append("timeout must be a positive number")

        # Check models structure
        if not isinstance(config.models, dict):
            errors.append("models must be a dictionary")
        else:
            for model_name, model_config in config.models.items():
                if not isinstance(model_config, dict):
                    errors.append(f"Model '{model_name}' config must be a dictionary")
                    continue

                # Check pose if present
                if 'pose' in model_config:
                    pose = model_config['pose']
                    if not isinstance(pose, dict):
                        errors.append(f"Model '{model_name}' pose must be a dictionary")
                    else:
                        if 'position' not in pose:
                            errors.append(f"Model '{model_name}' pose missing 'position'")
                        if 'orientation' not in pose:
                            errors.append(f"Model '{model_name}' pose missing 'orientation'")

        return len(errors) == 0, errors

    @staticmethod
    def print_config_summary(config: DemoConfig) -> None:
        """Print human-readable config summary.

        Args:
            config: DemoConfig to display
        """
        print("=" * 70)
        print("  Demo Configuration")
        print("=" * 70)
        print(f"Demo Name:     {config.demo_name}")
        print(f"Description:   {config.description}")
        print(f"Gazebo World:  {config.gazebo_world}")
        print(f"Timeout:       {config.timeout}s")
        print(f"Models:        {len(config.models)}")

        if config.models:
            print("\nModel Details:")
            for model_name, model_config in config.models.items():
                print(f"  • {model_name}")
                if 'sdf_file' in model_config:
                    print(f"    └─ SDF: {model_config['sdf_file']}")
                if 'pose' in model_config:
                    pose = model_config['pose']
                    print(f"    └─ Position: {pose.get('position', 'N/A')}")
                    print(f"    └─ Orientation: {pose.get('orientation', 'N/A')}")

        if config.extra:
            print("\nAdditional Configuration:")
            for key, value in config.extra.items():
                print(f"  • {key}: {value}")

        print("=" * 70)
