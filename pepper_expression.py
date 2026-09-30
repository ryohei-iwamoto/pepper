"""Pepper-specific output adaptation, separate from the conversation state."""
import math


def adapt_expression(command, snapshot):
    """Keep speech/action/gaze; constrain expression intensity using computed arousal."""
    result = dict(command)
    arousal = snapshot["self"]["arousal"]
    proposed = float(result.get("intensity", 1.0))
    if not math.isfinite(proposed):
        proposed = 1.0
    # Keep the existing label as an expressive choice (e.g. thinking/grateful).
    # It is never fed back into the state engine.
    ceiling = 0.8 + 0.7 * arousal
    result["intensity"] = max(0.3, min(ceiling, proposed))
    return result
