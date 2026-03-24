#!/usr/bin/env python
"""
Terminal chat interface for testing NeuroTwin.

Usage:
    uv run python chat.py --user <user_id>
    uv run python chat.py --email <email>

Requirements: Allows testing Twin responses through terminal
"""

import os
import sys
import django
import argparse
from typing import Optional

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neurotwin.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.twin.models import Twin
from apps.csm.models import CSMProfile
from core.ai.services import AIService
from core.ai.dataclasses import AIConfig

User = get_user_model()


class TwinChat:
    """Terminal chat interface for NeuroTwin."""
    
    def __init__(self, user):
        self.user = user
        self.twin = Twin.get_for_user(str(user.id))
        
        if not self.twin:
            print(f"❌ No Twin found for user {user.email}")
            print("Please complete onboarding first.")
            sys.exit(1)
        
        if not self.twin.is_active:
            print(f"⚠️  Twin is deactivated for user {user.email}")
            print("Reactivate your Twin to continue.")
            sys.exit(1)
        
        self.csm_profile = self.twin.csm_profile
        self.ai_service = AIService()
        
        print(f"\n✨ NeuroTwin Chat Interface")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"User: {user.email}")
        print(f"Model: {self.twin.model}")
        print(f"Cognitive Blend: {self.twin.cognitive_blend}% ({self.twin.blend_mode})")
        if self.twin.requires_confirmation:
            print(f"⚠️  High blend mode - actions require confirmation")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    def run(self):
        """Start the chat loop."""
        print("Type your message and press Enter. Type 'exit', 'quit', or Ctrl+C to end.\n")
        
        conversation_history = []
        
        try:
            while True:
                # Get user input
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\n👋 Goodbye!")
                    break
                
                # Handle special commands
                if user_input.startswith('/'):
                    self._handle_command(user_input)
                    continue
                
                # Generate Twin response
                print("Twin: ", end='', flush=True)
                response = self._generate_response(user_input, conversation_history)
                print(response)
                print()
                
                # Update conversation history
                conversation_history.append({
                    'role': 'user',
                    'content': user_input
                })
                conversation_history.append({
                    'role': 'assistant',
                    'content': response
                })
                
                # Keep only last 10 exchanges
                if len(conversation_history) > 20:
                    conversation_history = conversation_history[-20:]
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            sys.exit(0)
    
    def _generate_response(self, user_message: str, history: list) -> str:
        """Generate Twin response using AI service."""
        try:
            # Get CSM profile data
            csm_profile_data = self.csm_profile.get_profile_data().to_dict()
            
            # Build prompt with conversation history
            if history:
                context = "\n".join([
                    f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                    for msg in history[-6:]  # Last 3 exchanges
                ])
                prompt = f"Previous conversation:\n{context}\n\nUser: {user_message}"
            else:
                prompt = user_message
            
            # Generate response - use AIModel from core.ai.dataclasses
            from core.ai.dataclasses import AIModel
            ai_response = self.ai_service.generate_response(
                prompt=prompt,
                csm_profile_data=csm_profile_data,
                cognitive_blend=self.twin.cognitive_blend,
                model=AIModel(self.twin.model)
            )
            
            return ai_response.content
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"❌ Error generating response: {str(e)}"
    
    def _handle_command(self, command: str):
        """Handle special commands."""
        cmd = command.lower().strip()
        
        if cmd == '/help':
            print("\nAvailable commands:")
            print("  /help     - Show this help message")
            print("  /status   - Show Twin status")
            print("  /blend    - Show cognitive blend info")
            print("  /profile  - Show CSM profile summary")
            print("  exit/quit - Exit chat\n")
        
        elif cmd == '/status':
            print(f"\n📊 Twin Status:")
            print(f"  Active: {'✅' if self.twin.is_active else '❌'}")
            print(f"  Kill Switch: {'🔴 ACTIVE' if self.twin.kill_switch_active else '✅ Inactive'}")
            print(f"  Model: {self.twin.model}")
            print(f"  Created: {self.twin.created_at.strftime('%Y-%m-%d %H:%M')}\n")
        
        elif cmd == '/blend':
            print(f"\n🎚️  Cognitive Blend:")
            print(f"  Value: {self.twin.cognitive_blend}%")
            print(f"  Mode: {self.twin.blend_mode}")
            print(f"  Requires Confirmation: {'Yes' if self.twin.requires_confirmation else 'No'}")
            
            if self.twin.cognitive_blend <= 30:
                print(f"  Behavior: Pure AI logic with minimal personality")
            elif self.twin.cognitive_blend <= 70:
                print(f"  Behavior: Balanced blend of personality + AI reasoning")
            else:
                print(f"  Behavior: Heavy personality mimicry\n")
        
        elif cmd == '/profile':
            if self.csm_profile:
                profile_data = self.csm_profile.get_profile_data()
                print(f"\n👤 CSM Profile (v{self.csm_profile.version}):")
                print(f"  Personality:")
                print(f"    Openness: {profile_data.personality.openness:.2f}")
                print(f"    Conscientiousness: {profile_data.personality.conscientiousness:.2f}")
                print(f"    Extraversion: {profile_data.personality.extraversion:.2f}")
                print(f"  Tone:")
                print(f"    Formality: {profile_data.tone.formality:.2f}")
                print(f"    Warmth: {profile_data.tone.warmth:.2f}")
                print(f"    Directness: {profile_data.tone.directness:.2f}")
                print(f"  Communication:")
                print(f"    Response Length: {profile_data.communication.response_length}")
                print(f"    Emoji Usage: {profile_data.communication.emoji_usage}\n")
            else:
                print("\n❌ No CSM profile found\n")
        
        else:
            print(f"\n❌ Unknown command: {command}")
            print("Type /help for available commands\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Terminal chat interface for testing NeuroTwin'
    )
    parser.add_argument(
        '--user',
        type=str,
        help='User ID (UUID)'
    )
    parser.add_argument(
        '--email',
        type=str,
        help='User email address'
    )
    
    args = parser.parse_args()
    
    # Find user
    user = None
    if args.user:
        try:
            user = User.objects.get(id=args.user)
        except User.DoesNotExist:
            print(f"❌ User with ID {args.user} not found")
            sys.exit(1)
    elif args.email:
        try:
            user = User.objects.get(email=args.email)
        except User.DoesNotExist:
            print(f"❌ User with email {args.email} not found")
            sys.exit(1)
    else:
        # List available users
        users = User.objects.all()[:10]
        if not users:
            print("❌ No users found in database")
            sys.exit(1)
        
        print("\nAvailable users:")
        for i, u in enumerate(users, 1):
            twin = Twin.get_for_user(str(u.id))
            status = "✅ Twin" if twin else "❌ No Twin"
            print(f"  {i}. {u.email} ({status})")
        
        print("\nUsage:")
        print("  python chat.py --email <email>")
        print("  python chat.py --user <user_id>")
        sys.exit(0)
    
    # Start chat
    chat = TwinChat(user)
    chat.run()


if __name__ == '__main__':
    main()
