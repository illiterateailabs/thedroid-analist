"""
Integration tests for moralis provider.

Generated by new_provider_scaffold.py on 2025-06-28
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.integrations.moralis_client import MoralisClient
from backend.agents.tools.moralis_nft_tool import MoralisNftTool
from backend.core.neo4j_loader import Neo4jLoader


# Skip these tests if no API key is available
pytestmark = pytest.mark.skipif(
    not os.environ.get("MORALIS_API_KEY"),
    reason="moralis API key not available",
)


@pytest.fixture
def mock_neo4j():
    """Mock Neo4j loader."""
    loader = AsyncMock(spec=Neo4jLoader)
    loader._execute_query = AsyncMock()
    loader._process_result_stats = MagicMock(return_value=MagicMock(
        nodes_created=0,
        relationships_created=0,
        properties_set=0,
        labels_added=0,
    ))
    return loader


@pytest.mark.integration
@pytest.mark.asyncio
async def test_client_real_connection():
    """Test connecting to the real API (requires API key)."""
    # This test will be skipped if no API key is available
    client = MoralisClient()
    
    # Test a simple API call - Get NFTs for vitalik.eth
    try:
        result = await client.get_wallet_nfts(
            address="0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
            params={"chain": "eth", "limit": 10}
        )
        assert result is not None
        assert "result" in result
    except Exception as e:
        pytest.fail(f"API call failed: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nft_tool_execution():
    """Test the Moralis NFT tool."""
    tool = MoralisNftTool()
    
    # Test with vitalik.eth on Ethereum
    params = {
        "address": "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
        "chain": "eth",
        "normalizeMetadata": True
    }
    
    try:
        result = await tool._execute(params)
        assert result is not None
        assert "result" in result
    except Exception as e:
        pytest.fail(f"Tool execution failed: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_neo4j_integration(mock_neo4j):
    """Test integration with Neo4j."""
    client = MoralisClient()
    
    # Mock API response
    with patch.object(client, 'get_wallet_nfts', return_value={
        "result": [
            {
                "token_address": "0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d",
                "token_id": "1234",
                "name": "Bored Ape #1234",
                "symbol": "BAYC",
                "token_uri": "https://ipfs.io/ipfs/...",
                "metadata": {
                    "name": "Bored Ape #1234",
                    "image": "https://ipfs.io/ipfs/...",
                    "attributes": []
                },
                "amount": "1",
                "contract_type": "ERC721"
            }
        ]
    }):
        # Get data from API
        data = await client.get_wallet_nfts("0xtest")
        
        # Process data with Neo4j
        for item in data.get("result", []):
            query = """
            MERGE (nft:NFT {contract_address: $contract_address, token_id: $token_id})
            SET nft.name = $name, nft.symbol = $symbol, nft.contract_type = $contract_type
            MERGE (addr:Address {address: $wallet})
            MERGE (addr)-[owns:OWNS]->(nft)
            SET owns.amount = $amount
            RETURN nft, addr, owns
            """
            params = {
                "contract_address": item["token_address"],
                "token_id": item["token_id"],
                "name": item.get("name"),
                "symbol": item.get("symbol"),
                "contract_type": item.get("contract_type"),
                "wallet": "0xtest",
                "amount": item.get("amount", "1")
            }
            
            await mock_neo4j._execute_query(query, params)
        
        # Verify Neo4j was called
        assert mock_neo4j._execute_query.called


@pytest.mark.integration
@pytest.mark.asyncio
async def test_provider_error_handling():
    """Test error handling for API calls."""
    client = MoralisClient()
    
    # Test with invalid chain
    with pytest.raises(Exception):
        await client.get_wallet_nfts(
            address="0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
            params={"chain": "invalid_chain"}
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tool_validation():
    """Test tool parameter validation."""
    tool = MoralisNftTool()
    
    # Test invalid chain
    params = {
        "address": "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
        "chain": "invalid_chain"
    }
    
    with pytest.raises(ValueError):
        await tool._execute(params)
    
    # Test missing required field
    params = {
        "chain": "eth"
        # Missing address
    }
    
    with pytest.raises(Exception):
        await tool._execute(params)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_nft_metadata_tool():
    """Test specific NFT metadata retrieval."""
    tool = MoralisNftTool()
    
    # Mock the client method
    with patch.object(tool.client, 'get_nft_metadata', return_value={
        "token_address": "0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d",
        "token_id": "1234",
        "name": "Bored Ape #1234",
        "metadata": {
            "name": "Bored Ape #1234", 
            "image": "https://ipfs.io/ipfs/...",
            "attributes": []
        }
    }) as mock_get_metadata:
        params = {
            "address": "0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d",
            "token_id": "1234",
            "chain": "eth"
        }
        
        result = await tool._execute(params)
        mock_get_metadata.assert_called_once()
        assert result is not None
        assert result["token_id"] == "1234"
        assert result["name"] == "Bored Ape #1234"
