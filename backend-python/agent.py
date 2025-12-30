class WakeyAgent:
    """
    Rule-based agent for Wakey alarm responses.
    Generates contextual messages based on snooze count and actions.
    """
    
    # Tone thresholds
    SOFT_THRESHOLD = 2
    PLAYFUL_THRESHOLD = 4
    STRICT_THRESHOLD = 6
    
    def __init__(self):
        self.messages = {
            'soft': {
                'snooze': [
                    "No worries, take 5 more minutes! ☀️",
                    "Rest a bit longer, you've got this!",
                    "A little extra sleep never hurt anyone 😴"
                ],
                'acknowledge': [
                    "Great job waking up! Have an amazing day! 🌟",
                    "You're up! Hope today treats you well! ✨",
                    "Morning champion! Let's make today count! 💪"
                ],
                'cancel': [
                    "Alarm cancelled. Hope everything's okay! 💙"
                ]
            },
            'playful': {
                'snooze': [
                    "Again? Your bed must be really comfy 😏",
                    "Okay okay, but this is the last one... right? 😅",
                    "Someone's testing the limits today! ⏰",
                    "Your friend is probably judging you rn 👀"
                ],
                'acknowledge': [
                    "Finally! Your bed was holding you hostage 😂",
                    "Look who decided to join the land of the living! 🎉",
                    "You're up! Only took a few tries 😜"
                ],
                'cancel': [
                    "Alarm cancelled. Sweet dreams, I guess? 😴"
                ]
            },
            'strict': {
                'snooze': [
                    "Seriously? You're making your friend wait. GET UP! 🚨",
                    "This is getting ridiculous. Up. NOW. ⚠️",
                    "Your snooze button is not your friend. WAKE UP! 💥",
                    "You're disappointing everyone, including yourself. 😤"
                ],
                'acknowledge': [
                    "About time. Don't let this happen again. 😐",
                    "You're up. Barely acceptable. ⏱️",
                    "Finally awake. Let's not repeat this tomorrow. 💼"
                ],
                'cancel': [
                    "Alarm cancelled. This better be important. 😠"
                ]
            },
            'cancel_notify_other': {
                'soft': [
                    "Your friend had to cancel the alarm. Hope they're okay! 💙"
                ],
                'playful': [
                    "Your wake-up buddy bailed on you! Guess you're solo today 😅",
                    "Looks like your friend hit the escape button 🏃‍♂️"
                ],
                'strict': [
                    "Your accountability partner cancelled. Don't use this as an excuse to sleep in. ⚠️"
                ]
            }
        }
    
    def _get_tone(self, snooze_count, alarm_tone=None):
        """
        Determine agent tone based on snooze count or alarm-level override.
        """
        if alarm_tone and alarm_tone in ['soft', 'playful', 'strict']:
            return alarm_tone
        
        if snooze_count < self.SOFT_THRESHOLD:
            return 'soft'
        elif snooze_count < self.PLAYFUL_THRESHOLD:
            return 'playful'
        else:
            return 'strict'
    
    def _get_message(self, tone, action, snooze_count=0):
        """
        Get a contextual message based on tone and action.
        """
        import random
        
        if action not in self.messages[tone]:
            return ""
        
        messages = self.messages[tone][action]
        return random.choice(messages)
    
    def snooze_alarm(self, alarm, user_id):
        """
        Handle snooze action: increment count, determine tone, generate message.
        """
        user_id_str = str(user_id)
        
        # Initialize snoozeCount if missing
        if 'snoozeCount' not in alarm:
            alarm['snoozeCount'] = {}
        
        # Increment snooze count
        current_count = alarm['snoozeCount'].get(user_id_str, 0)
        alarm['snoozeCount'][user_id_str] = current_count + 1
        
        # Get tone (check for alarm-level override)
        alarm_tone = alarm.get('tone', None)
        tone = self._get_tone(alarm['snoozeCount'][user_id_str], alarm_tone)
        
        # Generate message
        message = self._get_message(tone, 'snooze', alarm['snoozeCount'][user_id_str])
        
        alarm['agentMessage'] = message
        alarm['agentTone'] = tone
        
        return alarm
    
    def acknowledge_alarm(self, alarm, user_id):
        """
        Handle acknowledge action: mark as acknowledged, generate message.
        Only generate message on FIRST acknowledgement.
        """
        user_id_str = str(user_id)
        
        # Initialize acknowledged list if missing
        if 'acknowledged' not in alarm:
            alarm['acknowledged'] = []
        
        # Check if already acknowledged
        if user_id in alarm['acknowledged']:
            # Already acknowledged - return without message
            alarm['agentMessage'] = ""
            alarm['agentTone'] = ""
            return alarm
        
        # First acknowledgement - add to list
        alarm['acknowledged'].append(user_id)
        
        # Get snooze count for tone determination
        snooze_count = alarm.get('snoozeCount', {}).get(user_id_str, 0)
        alarm_tone = alarm.get('tone', None)
        tone = self._get_tone(snooze_count, alarm_tone)
        
        # Generate message
        message = self._get_message(tone, 'acknowledge', snooze_count)
        
        alarm['agentMessage'] = message
        alarm['agentTone'] = tone
        
        # Check if both users acknowledged - deactivate alarm
        user1_id = alarm['user1Id']
        user2_id = alarm['user2Id']
        
        if user1_id in alarm['acknowledged'] and user2_id in alarm['acknowledged']:
            alarm['isActive'] = False
        
        return alarm
    
    def cancel_alarm(self, alarm, user_id):
        """
        Handle cancel action: mark as cancelled, generate messages for both users.
        """
        user_id_str = str(user_id)
        
        # Mark who cancelled
        alarm['cancelledBy'] = user_id
        alarm['isActive'] = False
        
        # Get tone
        snooze_count = alarm.get('snoozeCount', {}).get(user_id_str, 0)
        alarm_tone = alarm.get('tone', None)
        tone = self._get_tone(snooze_count, alarm_tone)
        
        # Message for canceller
        cancel_message = self._get_message(tone, 'cancel')
        
        # Message for the other user (notification)
        import random
        other_user_message = random.choice(self.messages['cancel_notify_other'][tone])
        
        alarm['agentMessage'] = cancel_message
        alarm['agentTone'] = tone
        alarm['cancelNotifyMessage'] = other_user_message  # For the friend
        
        return alarm
    
    def get_alarm_status(self, alarm, user_id):
        """
        Get current status message for an alarm without modifying it.
        Useful for checking state without triggering actions.
        """
        user_id_str = str(user_id)
        snooze_count = alarm.get('snoozeCount', {}).get(user_id_str, 0)
        
        if snooze_count == 0:
            return {
                'message': 'Alarm is ready',
                'tone': 'soft',
                'snoozeCount': 0
            }
        
        alarm_tone = alarm.get('tone', None)
        tone = self._get_tone(snooze_count, alarm_tone)
        
        return {
            'message': f'Snoozed {snooze_count} time(s)',
            'tone': tone,
            'snoozeCount': snooze_count
        }