import pytest
from pathlib import Path
from contract_coding.schema.parser import parse_contract, ContractParserError
from contract_coding.schema.contract import LanguageContract
from pydantic import ValidationError

def test_parse_valid_contract():
    yaml_content = """
    version: "1.0"
    intent: "Test intent"
    modules:
      - name: "M-A"
        description: "Module A"
    topology:
      - source: "M-A"
        target: "M-B"
    """
    contract = parse_contract(yaml_content)
    assert isinstance(contract, LanguageContract)
    assert contract.intent == "Test intent"
    assert len(contract.modules) == 1
    assert contract.modules[0].name == "M-A"
    assert len(contract.topology) == 1

def test_parse_invalid_module_name():
    yaml_content = """
    version: "1.0"
    intent: "Test intent"
    modules:
      - name: "INVALID-NAME"
        description: "Module"
    """
    with pytest.raises(ContractParserError) as exc_info:
        parse_contract(yaml_content)
    assert "must match pattern" in str(exc_info.value)

def test_parse_invalid_yaml():
    with pytest.raises(ContractParserError):
        parse_contract("invalid: yaml: :")

def test_parse_missing_required_fields():
    yaml_content = """
    version: "1.0"
    # intent is missing
    modules: []
    """
    with pytest.raises(ContractParserError):
        parse_contract(yaml_content)
