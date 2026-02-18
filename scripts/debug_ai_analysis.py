#!/usr/bin/env python3
"""Debug AI analysis - see exactly what AI sees and decides"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from swindle_bot_v5_admin import WhatsAppBot, Config, AIAnalyzer
import json

print("="*60)
print(" AI ANALYSIS DEBUG")
print("="*60)

config = Config()
bot = WhatsAppBot(config)
ai = AIAnalyzer(config.ANTHROPIC_API_KEY)

print("\n🚀 Initializing Chrome...")
if not bot.initialize():
    print("❌ Failed to initialize")
    exit(1)

print("✅ Chrome initialized\n")

try:
    print("="*60)
    print(f" FETCHING MESSAGES FROM: {config.GROUP_NAME}")
    print("="*60)

    messages = bot.get_all_messages(config.GROUP_NAME)

    if not messages:
        print("❌ No messages found")
        exit(1)

    print(f"\n✅ Found {len(messages)} messages\n")

    # Show all messages
    print("="*60)
    print(" ALL MESSAGES (RAW)")
    print("="*60)
    for i, msg in enumerate(messages, 1):
        print(f"{i:2}. [{msg['sender']}]: {msg['text'][:80]}...")

    print(f"\n{'='*60}")
    print(" RUNNING AI ANALYSIS WITH PRE-FILTERING")
    print('='*60)
    print("(Pre-filtering removes: messages before signup, quoted organizer messages)")

    # Run AI analysis
    result = ai.analyze_messages(messages)

    # Note: The AI analysis includes pre-filtering logic that:
    # 1. Finds "now taking names" organizer message
    # 2. Only analyzes messages from that point forward
    # 3. Filters out messages quoting the organizer announcement

    # Show results
    print(f"\n{'='*60}")
    print(" AI RESULTS")
    print('='*60)

    print(f"\nTotal count: {result['total_count']}")
    print(f"Summary: {result['summary']}")

    print(f"\n{'='*60}")
    print(" PLAYERS LIST")
    print('='*60)
    for player in result['players']:
        guests = player.get('guests', [])
        guest_text = f" (guests: {guests})" if guests else ""
        pref_text = f" - {player['preferences']}" if player.get('preferences') else ""
        print(f"  • {player['name']}{guest_text}{pref_text}")

    if result.get('changes'):
        print(f"\n{'='*60}")
        print(" CHANGES DETECTED")
        print('='*60)
        for change in result['changes']:
            print(f"  • {change}")

    # Now analyze which players shouldn't be there
    print(f"\n{'='*60}")
    print(" VERIFICATION")
    print('='*60)

    # Check each player against messages
    player_names = [p['name'] for p in result['players']]
    print("\nPlayers in result:")
    for name in player_names:
        # Find messages from this person
        their_messages = [m for m in messages if m['sender'] == name]
        print(f"\n  {name}:")
        if their_messages:
            for msg in their_messages:
                print(f"    - \"{msg['text'][:60]}...\"")
        else:
            print(f"    ⚠️  NO MESSAGES FOUND - This might be a guest or error!")

    # Check for names in result that aren't in messages
    message_senders = set(m['sender'] for m in messages)
    result_players = set(player_names)

    print(f"\n{'='*60}")
    print(" POSSIBLE ISSUES")
    print('='*60)

    # Players in result but not in messages (hallucinations)
    hallucinated = result_players - message_senders
    if hallucinated:
        print(f"\n⚠️  Names in result but NOT in messages (possible AI hallucination):")
        for name in hallucinated:
            print(f"    • {name}")

    # Check for organizer messages
    print(f"\n⚠️  Checking for organizer messages:")
    organizer_keywords = ["now taking names", "all on the list", "morning all"]
    for msg in messages:
        text_lower = msg['text'].lower()
        if any(keyword in text_lower for keyword in organizer_keywords):
            print(f"    • [{msg['sender']}]: \"{msg['text'][:60]}...\"")

except KeyboardInterrupt:
    print("\n\n👋 Interrupted")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    print("\n\n🧹 Closing Chrome...")
    bot.close()
    print("✅ Done")
