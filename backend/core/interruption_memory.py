"""
Interruption Memory & Emotional Learning System
Tracks interruptions and manages AIRIS's emotional responses
"""
import json
import os
from datetime import datetime
from pathlib import Path

class InterruptionMemory:
    """Manages interruption tracking and emotional state"""
    
    def __init__(self, db_path="backend/data/interruptions/memory.json"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load_data()
        self.current_session = self._create_session()
    
    def _load_data(self):
        """Load interruption history from disk"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    return json.load(f)
            except:
                return {"sessions": [], "patterns": {}}
        return {"sessions": [], "patterns": {}}
    
    def _save_data(self):
        """Save interruption history to disk"""
        with open(self.db_path, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def _create_session(self):
        """Create new session for current conversation"""
        session_id = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        return {
            "session_id": session_id,
            "start_time": datetime.now().isoformat(),
            "interruptions": 0,
            "apologies": 0,
            "emotional_state": "neutral",
            "context": None,
            "airis_notes": []
        }
    
    def record_interruption(self, context=None):
        """
        Record an interruption and return emotional response
        
        Args:
            context: What AIRIS was talking about when interrupted
            
        Returns:
            dict: {
                'count': interruption count,
                'emotional_state': current emotion,
                'response_prefix': what AIRIS should say
            }
        """
        self.current_session["interruptions"] += 1
        self.current_session["context"] = context
        count = self.current_session["interruptions"]
        
        # Determine emotional state based on interrupt count
        if count == 1:
            emotion = "polite"
            prefix = "Oh, you wanted to say something? Go ahead."
        elif count == 2:
            emotion = "slightly_annoyed"
            prefix = "Myra... can I finish? You keep cutting me off."
        elif count == 3:
            emotion = "annoyed"
            prefix = "Seriously? I'm trying to help you here. Let me talk."
        else:
            emotion = "very_annoyed"
            prefix = "OKAY. You know what? Just tell me what you need."
        
        self.current_session["emotional_state"] = emotion
        
        # Learn pattern
        self._learn_pattern(context, count)
        
        # Save immediately
        self._save_session()
        
        return {
            "count": count,
            "emotional_state": emotion,
            "response_prefix": prefix
        }
    
    def record_apology(self):
        """User apologized - reset interruption counter with grace"""
        self.current_session["apologies"] += 1
        old_count = self.current_session["interruptions"]
        self.current_session["interruptions"] = 0
        self.current_session["emotional_state"] = "forgiving"
        
        self.current_session["airis_notes"].append(
            f"User apologized after {old_count} interruptions - showing growth"
        )
        
        self._save_session()
        
        return {
            "emotional_state": "forgiving",
            "response": "Okay okay, I know you're excited. Let me explain properly this time?"
        }
    
    def _learn_pattern(self, context, count):
        """
        Learn from interruption patterns
        AIRIS analyzes when/why user interrupts
        Gets smarter over time with more data
        """
        if not context:
            return
        
        # Track context-specific interruptions
        if context not in self.data["patterns"]:
            self.data["patterns"][context] = {
                "total_interruptions": 0,
                "sessions": 0,
                "avg_interruptions": 0,
                "trend": "stable"  # stable, increasing, decreasing
            }
        
        pattern = self.data["patterns"][context]
        old_avg = pattern["avg_interruptions"]
        
        pattern["total_interruptions"] += 1
        pattern["sessions"] = len([s for s in self.data["sessions"] if s.get("context") == context])
        pattern["avg_interruptions"] = pattern["total_interruptions"] / max(pattern["sessions"], 1)
        
        # Detect trends (is user getting more patient or less patient over time?)
        if pattern["sessions"] > 5:  # Need enough data
            new_avg = pattern["avg_interruptions"]
            if new_avg > old_avg * 1.2:
                pattern["trend"] = "increasing"  # User getting MORE impatient
            elif new_avg < old_avg * 0.8:
                pattern["trend"] = "decreasing"  # User getting LESS impatient (learning!)
            else:
                pattern["trend"] = "stable"
        
        # AIRIS learns and generates insights
        insights = []
        
        if pattern["avg_interruptions"] > 2.5:
            insights.append(f"User very impatient during {context} - keep responses SHORT")
        elif pattern["avg_interruptions"] > 1.5:
            insights.append(f"User gets impatient during {context} - moderate detail only")
        
        if pattern["trend"] == "increasing":
            insights.append(f"User patience DECREASING on {context} - adapt faster!")
        elif pattern["trend"] == "decreasing":
            insights.append(f"User patience IMPROVING on {context} - strategy working!")
        
        # Store insights
        for insight in insights:
            if insight not in self.current_session["airis_notes"]:
                self.current_session["airis_notes"].append(insight)
    
    def _save_session(self):
        """Save current session to history"""
        # Update or add current session
        session_id = self.current_session["session_id"]
        existing = [s for s in self.data["sessions"] if s["session_id"] == session_id]
        
        if existing:
            # Update existing
            idx = self.data["sessions"].index(existing[0])
            self.data["sessions"][idx] = self.current_session
        else:
            # Add new
            self.data["sessions"].append(self.current_session)
        
        # NO LIMIT - Keep all sessions forever
        # AIRIS gets smarter the more she learns!
        
        self._save_data()
    
    def get_emotional_context(self):
        """
        Get current emotional state for LLM context
        
        Returns:
            str: Context to inject into system prompt
        """
        state = self.current_session["emotional_state"]
        count = self.current_session["interruptions"]
        
        if state == "neutral":
            return ""
        
        if state == "polite":
            return "User just interrupted you once - be polite but continue."
        
        if state == "slightly_annoyed":
            return f"User has interrupted you {count} times now. Show mild annoyance but stay helpful."
        
        if state == "annoyed":
            return f"User keeps interrupting ({count} times). Be direct - call it out firmly but don't be mean."
        
        if state == "very_annoyed":
            return f"User won't stop interrupting ({count}+ times). Be blunt. Make them explain what they actually need."
        
        if state == "forgiving":
            return "User apologized for interrupting. Be warm and understanding - give them a fresh start."
        
        return ""
    
    def reset_session(self):
        """Start a new conversation session"""
        self._save_session()
        self.current_session = self._create_session()
    
    def get_stats(self):
        """Get comprehensive interruption statistics"""
        total_sessions = len(self.data["sessions"])
        total_interruptions = sum(s["interruptions"] for s in self.data["sessions"])
        total_apologies = sum(s.get("apologies", 0) for s in self.data["sessions"])
        
        # Calculate averages
        avg_interruptions_per_session = total_interruptions / max(total_sessions, 1)
        
        # Find most patient and least patient sessions
        if self.data["sessions"]:
            best_session = min(self.data["sessions"], key=lambda s: s["interruptions"])
            worst_session = max(self.data["sessions"], key=lambda s: s["interruptions"])
        else:
            best_session = worst_session = None
        
        # Trend analysis over last 10 sessions
        recent_trend = "unknown"
        if total_sessions >= 10:
            last_10 = self.data["sessions"][-10:]
            first_5_avg = sum(s["interruptions"] for s in last_10[:5]) / 5
            last_5_avg = sum(s["interruptions"] for s in last_10[5:]) / 5
            
            if last_5_avg < first_5_avg * 0.7:
                recent_trend = "improving"  # User getting more patient!
            elif last_5_avg > first_5_avg * 1.3:
                recent_trend = "worsening"  # User getting less patient
            else:
                recent_trend = "stable"
        
        return {
            "current_session": self.current_session,
            "patterns": self.data["patterns"],
            "lifetime_stats": {
                "total_sessions": total_sessions,
                "total_interruptions": total_interruptions,
                "total_apologies": total_apologies,
                "avg_interruptions_per_session": round(avg_interruptions_per_session, 2),
                "best_session": best_session,
                "worst_session": worst_session,
                "recent_trend": recent_trend,
                "data_size_kb": len(json.dumps(self.data)) / 1024  # How big is memory
            }
        }