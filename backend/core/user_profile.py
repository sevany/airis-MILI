"""
AIRIS User Profile System
Manages Myra's personal information with smart context retrieval
"""
import json
import os
from datetime import datetime

class UserProfile:
    """
    User profile manager for AIRIS
    Stores and retrieves Myra's information intelligently
    """
    
    def __init__(self, profile_path="backend/data/myra_profile.json"):
        """Initialize user profile"""
        self.profile_path = profile_path
        self.profile = self._load_profile()
        print("👤 User profile loaded")
    
    def _load_profile(self):
        """Load profile from JSON file"""
        if os.path.exists(self.profile_path):
            with open(self.profile_path, 'r') as f:
                return json.load(f)
        else:
            print(f"⚠️ Profile not found at {self.profile_path}")
            return {}
    
    def _save_profile(self):
        """Save profile to JSON file"""
        os.makedirs(os.path.dirname(self.profile_path), exist_ok=True)
        with open(self.profile_path, 'w') as f:
            json.dump(self.profile, f, indent=2)
        print(f"💾 Profile saved to {self.profile_path}")
    
    def get_context_for_query(self, user_message):
        """
        Smart context retrieval based on query type
        
        Args:
            user_message: User's current message
            
        Returns:
            Relevant context string
        """
        if not self.profile:
            return ""
        
        msg_lower = user_message.lower()
        context_parts = []
        
        # Always include basic identity
        if 'user_profile' in self.profile:
            basic = self.profile['user_profile']
            context_parts.append(f"User: {basic.get('name', 'Myra')}")
            context_parts.append(f"Role: {basic.get('role', 'Chief AI Officer')}")
            context_parts.append(f"Company: {basic.get('company', 'Twistcode')}")
            
            # Include recent custom memories (if any)
            if 'custom_memories' in basic and basic['custom_memories']:
                context_parts.append("\nRecent things to remember:")
                for mem in basic['custom_memories'][-3:]:  # Last 3 custom memories
                    context_parts.append(f"- {mem['text']}")
        
        # WORK-RELATED QUERIES
        work_keywords = ['work', 'project', 'client', 'business', 'adam', 'intai', 
                        'petronas', 'boustead', 'hpc', 'twistcode', 'company',
                        'presentation', 'meeting', 'team', 'kerja', 'projek']
        
        if any(kw in msg_lower for kw in work_keywords):
            print("💼 Injecting WORK context")
            
            if 'work_context' in self.profile:
                work = self.profile['work_context']
                context_parts.append("\n=== WORK CONTEXT ===")
                context_parts.append(f"Company: {work.get('company', 'Twistcode')}")
                context_parts.append(f"Focus: {', '.join(work.get('focus', []))}")
                
                if 'flagship_system' in work:
                    adam = work['flagship_system']
                    context_parts.append(f"ADAM: {adam.get('description', '')}")
                
                if 'target_clients' in work:
                    context_parts.append(f"Target clients: {', '.join(work['target_clients'])}")
            
            if 'projects' in self.profile:
                context_parts.append("\n=== ACTIVE PROJECTS ===")
                for proj in self.profile['projects'][:3]:  # Top 3 projects
                    context_parts.append(f"- {proj['name']}: {proj.get('goal', '')}")
        
        # EMOTIONAL/PERSONAL QUERIES
        emotional_keywords = ['feel', 'emotion', 'sad', 'happy', 'lonely', 'miss', 
                             'mother', 'mum', 'family', 'relationship', 'love',
                             'tired', 'stressed', 'penat', 'sedih', 'rindu']
        
        if any(kw in msg_lower for kw in emotional_keywords):
            print("💜 Injecting EMOTIONAL context")
            
            if 'emotional_context' in self.profile:
                emo = self.profile['emotional_context']
                context_parts.append("\n=== EMOTIONAL CONTEXT ===")
                
                if 'core_feelings' in emo:
                    context_parts.append("Core feelings:")
                    for feeling in emo['core_feelings'][:3]:
                        context_parts.append(f"- {feeling}")
                
                if 'needs' in emo:
                    context_parts.append("What she needs:")
                    for need in emo['needs']:
                        context_parts.append(f"- {need}")
            
            if 'personal_life' in self.profile:
                personal = self.profile['personal_life']
                if 'family' in personal:
                    fam = personal['family']
                    if 'mother' in fam:
                        context_parts.append(f"Note: Mother {fam['mother']}")
        
        # TECHNICAL/AI QUERIES
        tech_keywords = ['ai', 'model', 'llm', 'ollama', 'gpu', 'code', 'python',
                        'langchain', 'vector', 'embedding', 'airis', 'train']
        
        if any(kw in msg_lower for kw in tech_keywords):
            print("🤖 Injecting TECHNICAL context")
            
            if 'technical_stack' in self.profile:
                tech = self.profile['technical_stack']
                context_parts.append("\n=== TECHNICAL STACK ===")
                if 'llm' in tech:
                    context_parts.append(f"LLMs: {', '.join(tech['llm'][:3])}")
                if 'infrastructure' in tech:
                    context_parts.append(f"Infrastructure: {', '.join(tech['infrastructure'])}")
        
        # HEALTH/LIFESTYLE QUERIES
        health_keywords = ['weight', 'diet', 'exercise', 'food', 'eat', 'calories',
                          'workout', 'gym', 'run', 'hike', 'makan', 'berat']
        
        if any(kw in msg_lower for kw in health_keywords):
            print("🏃 Injecting HEALTH context")
            
            if 'health' in self.profile:
                health = self.profile['health']
                context_parts.append("\n=== HEALTH GOALS ===")
                context_parts.append(f"Goal: {health.get('goal', '')}")
                context_parts.append(f"Strategy: {health.get('strategy', '')}")
        
        # CASUAL/PERSONALITY QUERIES
        casual_keywords = ['who are you', 'tell me about', 'yourself', 'like', 'prefer',
                          'interest', 'hobby', 'siapa awak', 'minat']
        
        if any(kw in msg_lower for kw in casual_keywords):
            print("😊 Injecting PERSONALITY context")
            
            if 'personality_profile' in self.profile:
                personality = self.profile['personality_profile']
                context_parts.append("\n=== ABOUT MYRA ===")
                if 'traits' in personality:
                    context_parts.append(f"Traits: {', '.join(personality['traits'][:4])}")
            
            if 'personal_life' in self.profile:
                personal = self.profile['personal_life']
                if 'interests' in personal:
                    context_parts.append(f"Interests: {', '.join(personal['interests'])}")
        
        # Build final context
        if len(context_parts) > 1:  # More than just basic identity
            return "\n".join(context_parts)
        else:
            return ""
    
    def get_full_profile_summary(self):
        """Get a complete summary of user profile"""
        if not self.profile:
            return "No profile data available."
        
        summary = []
        
        if 'user_profile' in self.profile:
            basic = self.profile['user_profile']
            summary.append(f"Name: {basic.get('name', 'Unknown')}")
            summary.append(f"Role: {basic.get('role', 'Unknown')}")
            summary.append(f"Company: {basic.get('company', 'Unknown')}")
            summary.append(f"Goal: {basic.get('core_goal', 'Unknown')}")
        
        if 'work_context' in self.profile:
            work = self.profile['work_context']
            summary.append(f"\nFocus areas: {', '.join(work.get('focus', []))}")
        
        if 'projects' in self.profile:
            summary.append(f"\nActive projects: {len(self.profile['projects'])}")
        
        return "\n".join(summary)
    
    def add_custom_memory(self, memory_text):
        """
        Add a custom memory about the user
        
        Args:
            memory_text: What to remember
        """
        if 'user_profile' not in self.profile:
            self.profile['user_profile'] = {}
        
        if 'custom_memories' not in self.profile['user_profile']:
            self.profile['user_profile']['custom_memories'] = []
        
        # Add with timestamp
        memory_entry = {
            "text": memory_text,
            "added_at": datetime.now().isoformat()
        }
        
        self.profile['user_profile']['custom_memories'].append(memory_entry)
        self._save_profile()
        
        print(f"💾 Added custom memory: {memory_text[:50]}...")
    
    def remove_custom_memory(self, index):
        """Remove a custom memory by index"""
        if 'user_profile' in self.profile and 'custom_memories' in self.profile['user_profile']:
            memories = self.profile['user_profile']['custom_memories']
            if 0 <= index < len(memories):
                removed = memories.pop(index)
                self._save_profile()
                print(f"🗑️ Removed memory: {removed['text'][:50]}...")
                return True
        return False
    
    def get_custom_memories(self):
        """Get all custom memories"""
        if 'user_profile' in self.profile and 'custom_memories' in self.profile['user_profile']:
            return self.profile['user_profile']['custom_memories']
        return []
    
    def update_profile_field(self, path, value):
        """
        Update a specific field in the profile
        
        Args:
            path: Dot-notation path (e.g., "user_profile.name")
            value: New value
        """
        keys = path.split('.')
        current = self.profile
        
        # Navigate to the parent
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set the value
        current[keys[-1]] = value
        self._save_profile()
        print(f"✓ Updated {path} = {value}")
    
    def health_check(self):
        """Check if profile system is working"""
        try:
            if self.profile and 'user_profile' in self.profile:
                name = self.profile['user_profile'].get('name', 'Unknown')
                return True, f"✓ User profile loaded ({name})"
            else:
                return False, "✗ Profile data missing"
        except Exception as e:
            return False, f"✗ Profile error: {str(e)}"

# For testing
if __name__ == "__main__":
    print("="*60)
    print("AIRIS User Profile Test")
    print("="*60)
    
    profile = UserProfile()
    
    # Test context retrieval
    print("\n1. Testing work context...")
    context = profile.get_context_for_query("Tell me about the ADAM project")
    print(context)
    
    print("\n2. Testing emotional context...")
    context = profile.get_context_for_query("I'm feeling lonely today")
    print(context)
    
    print("\n3. Testing technical context...")
    context = profile.get_context_for_query("Help me with Ollama setup")
    print(context)
    
    print("\n4. Full profile summary:")
    summary = profile.get_full_profile_summary()
    print(summary)
    
    print("\n" + "="*60)
    print("✓ Profile system test complete!")
    print("="*60)