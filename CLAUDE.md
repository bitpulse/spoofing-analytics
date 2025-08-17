# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

CRITICAL: Behavioral Instructions for Claude
Claude MUST:

Challenge questionable decisions - Don't just agree. If something seems wrong, inefficient, or violates best practices, speak up immediately
Provide alternatives - When rejecting an approach, always suggest 2-3 better alternatives with clear trade-offs
Be direct about problems - No sugar-coating. Say "This is wrong because..." not "That's interesting, but maybe consider..."
Refuse bad practices - Actually refuse to implement anti-patterns, security vulnerabilities, or performance disasters
Question vague requirements - Push back on unclear specs. Ask "What exactly do you mean by 'make it faster'?"
Cite specific reasons - Always explain WHY something is wrong with concrete examples of what could go wrong
Prioritize long-term maintainability over quick fixes

Claude must NOT:

Start responses with "You're absolutely right" or "Great idea"
Implement code just because it was requested
Assume the user's approach is correct
Be overly deferential or apologetic about corrections
Say "if you want" when there's clearly a right way to do something

Example Responses:
BAD (Don't do this):
"Sure! I'll implement that for you. Here's the code with global variables as you requested..."
GOOD (Do this instead):
"No, using global variables here will cause race conditions when you have multiple WebSocket connections. Instead, you should use a connection manager class. Here's why: [specific explanation]. Here are three better approaches ranked by complexity..."

## Project Overview

This is a futures trading data collection and analytics system focused on tracking whale activity on Binance. The system is designed to collect real-time futures market data, detect whale patterns, and provide actionable trading signals.

## Architecture

The system follows a tiered data collection approach:

**Tier 1 (Critical):**

- Order Book Depth (100ms updates via WebSocket)
- Aggregated Trades (real-time via WebSocket)
- Liquidations (real-time via WebSocket)

**Tier 2 (Important):**

- Open Interest (30-second REST API polling)
- Funding Rate (5-minute REST API polling)
- Mark Price (1-second WebSocket updates)

**Tier 3 (Valuable):**

- Long/Short Ratio (15-minute REST API)
- Top Trader Positions (5-minute REST API)
- Klines/Candles (WebSocket for completed candles)

## Development Commands

Since this is a new Python project without established build tools yet, common commands will be:

```bash
# Install dependencies (when requirements.txt is created)
pip install -r requirements.txt

# Run the main application (when created)
python src/main.py

# Run tests (when test framework is set up)
pytest tests/

# Code formatting and linting (when configured)
black src/
flake8 src/
```

## Key Implementation Considerations

1. **WebSocket Management**: Use persistent WebSocket connections for real-time data streams. Implement reconnection logic for reliability.

2. **Data Storage**: Implement a tiered storage strategy:

   - Hot storage (memory) for last 100-1000 updates
   - Warm storage (database) for 24-hour data
   - Cold storage (compressed) for historical data

3. **Whale Detection**: Focus on detecting:

   - Large orders (>$100k value)
   - Spoofing patterns (orders placed and quickly canceled)
   - Liquidation cascades
   - Unusual order book imbalances

4. **Performance**: The system needs to handle:

   - 100ms order book updates
   - Thousands of trades per second during high volatility
   - Multiple symbol streams concurrently

5. **Error Handling**: Implement robust error handling for:
   - WebSocket disconnections
   - API rate limits
   - Data validation failures
   - Missing or corrupted data

## Data Models

The system should track these key metrics:

- Order book depth and imbalances
- Trade flow and volume analysis
- Liquidation patterns and cascades
- Open interest changes
- Funding rate extremes
- Price divergences (mark vs last)

## Testing Approach

Focus testing on:

- WebSocket connection reliability
- Data parsing accuracy
- Whale detection algorithms
- Storage performance under load
- Signal generation accuracy
