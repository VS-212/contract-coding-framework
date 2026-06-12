import yaml
from pathlib import Path
from pydantic import ValidationError
from typing import Union
from .contract import LanguageContract

class ContractParserError(Exception):
    """Custom exception for contract parsing errors."""
    pass

def parse_contract(source: Union[str, Path]) -> LanguageContract:
    """
    Parses a YAML Language Contract into a validated Pydantic model.
    """
    try:
        is_file_path = False
        if isinstance(source, Path):
            is_file_path = True
            path_obj = source
        elif isinstance(source, str):
            try:
                if '\n' not in source and len(source) < 255:
                    path_obj = Path(source)
                    is_file_path = path_obj.is_file()
            except OSError:
                pass
                
        if is_file_path:
            with open(path_obj, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        else:
            data = yaml.safe_load(source)
            
        if not isinstance(data, dict):
            raise ContractParserError("Contract must be a valid YAML dictionary.")
            
        return LanguageContract(**data)
        
    except yaml.YAMLError as e:
        raise ContractParserError(f"YAML parsing failed: {e}")
    except ValidationError as e:
        raise ContractParserError(f"Contract validation failed: {e}")
    except Exception as e:
        raise ContractParserError(f"Unexpected error during parsing: {e}")
