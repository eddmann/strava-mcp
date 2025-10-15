"""Helper functions for tests."""

from typing import TYPE_CHECKING

from mcp.types import (
    BlobResourceContents,
    PromptMessage,
    TextContent,
    TextResourceContents,
)

if TYPE_CHECKING:
    from fastmcp.client.client import CallToolResult


def get_text_content(result: "CallToolResult") -> str:
    """Extract text content from a CallToolResult.

    Args:
        result: The result from calling a tool

    Returns:
        The text content from the result

    Raises:
        AssertionError: If content is not TextContent
    """
    assert len(result.content) > 0, "Result has no content"
    content = result.content[0]
    assert isinstance(content, TextContent), f"Expected TextContent, got {type(content)}"
    return content.text


def get_prompt_text(message: PromptMessage) -> str:
    """Extract text from a PromptMessage.

    Args:
        message: The prompt message

    Returns:
        The text content from the message

    Raises:
        AssertionError: If content is not TextContent
    """
    content = message.content
    assert isinstance(content, TextContent), f"Expected TextContent, got {type(content)}"
    return content.text


def get_resource_text(contents: TextResourceContents | BlobResourceContents) -> str:
    """Extract text from resource contents.

    Args:
        contents: The resource contents (from read_resource result)

    Returns:
        The text from the resource

    Raises:
        AssertionError: If contents is not TextResourceContents
    """
    assert isinstance(contents, TextResourceContents), (
        f"Expected TextResourceContents, got {type(contents)}"
    )
    return contents.text
