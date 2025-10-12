#!/bin/bash
# Script to download spaCy French language model

set -e

echo "Downloading spaCy French language model..."

# Try to download the large model first
if python -m spacy download fr_core_news_md --quiet 2>/dev/null; then
    echo "✅ Successfully downloaded fr_core_news_md"
else
    echo "⚠️  Failed to download fr_core_news_md, trying fr_core_news_sm as fallback..."
    if python -m spacy download fr_core_news_sm --quiet 2>/dev/null; then
        echo "✅ Successfully downloaded fr_core_news_sm (fallback)"
    else
        echo "❌ Failed to download spaCy French model"
        exit 1
    fi
fi

echo "spaCy French model installed successfully"
