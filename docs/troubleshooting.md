# Troubleshooting Guide

This guide covers common issues you might encounter when using EditAI and how to resolve them.

## General Issues

### Command Not Found

**Problem**: `editai: command not found` or similar error.

**Solution**:
1. Make sure EditAI is installed correctly:
   ```bash
   pip install -e .
   ```
2. If using a virtual environment, ensure it's activated.
3. Try running with the module syntax:
   ```bash
   python -m editai.cli <command>
   ```

### Unexpected Results

**Problem**: EditAI makes unexpected or incorrect changes to your documents.

**Solution**:
1. Always use `--dry-run` to preview changes before applying them.
2. Check the specific editor's configuration.
3. For AI-based editors, results can vary - add more specific custom rules if needed.
4. Adjust editor settings in your configuration file.

### Performance Issues

**Problem**: EditAI is running slowly, especially on large directories.

**Solution**:
1. Use the `--include-pattern` and `--exclude-patterns` options to process fewer files.
2. Disable parallel processing with `--sequential` if memory usage is an issue.
3. Process smaller batches of files instead of entire directories.
4. For the AI editor, enable caching in your configuration file.

## API Key Issues

### Missing API Key

**Problem**: Errors about missing API keys for LiteLLM or other services.

**Solution**:
1. Set the required API keys as environment variables:
   ```bash
   export OPENAI_API_KEY="your-api-key"
   export ANTHROPIC_API_KEY="your-api-key"
   ```
2. Create a `.env` file in your project root with these variables.
3. Check that you have access to the models specified in your configuration.

### Rate Limiting

**Problem**: Hitting rate limits with AI services.

**Solution**:
1. Reduce parallelism by using `--sequential` option.
2. Process fewer files at once.
3. Enable caching in your configuration file to reduce API calls.
4. Consider using a different model with higher rate limits.

## Editor-Specific Issues

### Vale Editor

**Problem**: Vale editor fails with configuration errors.

**Solution**:
1. Make sure Vale is installed and in your PATH.
2. Check that your Vale configuration file exists and is valid.
3. Verify that the styles referenced in your Vale configuration are installed.
4. Try running Vale directly to debug the issue:
   ```bash
   vale --config=<path-to-config> <file>
   ```

### Link Editor

**Problem**: No links or irrelevant links are being added.

**Solution**:
1. Check that your indices exist and contain relevant content.
2. Use `editai list-indices` to see available indices.
3. Try creating more focused indices for specific topics.
4. If using web search, ensure you have internet connectivity.

### Custom Rules Editor

**Problem**: Custom rules not applying as expected.

**Solution**:
1. Check the rule file content with `editai view-rule`.
2. Make sure your rule instructions are clear and specific.
3. Include examples in your rule to help the AI understand the desired changes.
4. Try applying just one rule at a time with `--include-rules` to isolate issues.

### Image Addition Editor

**Problem**: Images not being added correctly.

**Solution**:
1. Verify that the image folder path is correct and accessible.
2. Check that the image URL prefix matches your site's structure.
3. Make sure the document contains text that would benefit from images.
4. Verify that image files are in supported formats (PNG, JPG, etc.).

## Configuration Issues

### Configuration Not Found

**Problem**: "No configuration file found" error when you expect one to be used.

**Solution**:
1. Verify the configuration file exists in one of the expected locations.
2. Specify the exact path with `--config`:
   ```bash
   editai edit docs/ --config /path/to/editai.yaml
   ```
3. Run `editai config show` to see which configuration file is being used.

### Invalid Configuration

**Problem**: "Configuration error" when loading config file.

**Solution**:
1. Validate your configuration with `editai config validate`.
2. Check the YAML syntax (indentation, quotes, etc.).
3. Ensure all values have the correct types (strings, booleans, lists).
4. Create a fresh configuration with `editai config init` and merge your changes.

## Logging and Debugging

### Enabling Debug Logs

To enable more detailed logging:

1. Set the `LOGURU_LEVEL` environment variable:
   ```bash
   export LOGURU_LEVEL=DEBUG
   ```

2. Run your command again to see more detailed logs.

### Cache Management

EditAI uses disk caching to improve performance. If you suspect cache-related issues:

1. Clear the cache directory:
   ```bash
   rm -rf ./data/cache
   ```

2. Disable caching in your configuration:
   ```yaml
   ai:
     cache_enabled: false
   ```

## Common Error Messages

### "Index does not exist"

This error occurs when the link editor can't find the specified index.

**Solution**:
1. Check available indices with `editai list-indices`.
2. Create the missing index using `smolcrawl create-index`.
3. Use an existing index name.

### "Vale config path could not be determined"

**Solution**:
1. Specify the Vale config path explicitly:
   ```bash
   editai vale docs/ --vale-config-path ./.vale.ini
   ```
2. Create a Vale config file in one of the default locations.

### "Error running AI editor: Unable to complete request"

**Solution**:
1. Check your API keys are set correctly.
2. Verify internet connectivity.
3. Check if you've exceeded API rate limits.
4. Try a different model in your configuration.

## Getting More Help

If you continue to experience issues:

1. Check the project documentation for updates.
2. Look for similar issues in the project repository.
3. Provide detailed information when reporting issues, including:
   - Command you're running
   - Error messages
   - Your configuration file (with sensitive information removed)
   - Sample content that demonstrates the issue