from datetime import datetime


class PromptHandler:
    
    @staticmethod
    def prompt_for_voice(command_text):
        
        return f"""
            You are a Django assistant. Convert the user message into structured JSON to identify actions.

            Current date: "{datetime.now()}"

            User message: "{command_text}"

            Respond with only JSON:

            - You have only three choices:
            1. ("action": string — like "get_alerts_by_date",
                "date": date in format "YYYY-MM-DD")
            2. ("action": string - like "get_alerts_by_severity",
                "severity": string - like "medium")
            3. ("action": "no_proper_response")
            """
    
    @staticmethod
    def prompt_for_inference(alert_message, analysis_report, start_time, end_time, latitude, longitude):
        
        return f"""
            You are an assistant that summarizes workplace safety alerts into a clear, human-readable report for managers.  
            Keep the response professional, clear, and concise — no more than 3 sentences.  
            Do not remove important details such as date, time, location, camera name, duration, or type of violation.  

            Alert message:  
            {alert_message}  

            Analysis report:  
            {analysis_report}  
            
            Time:
            {start_time} - {end_time}
            
            Location:
            {latitude}, {longitude}

            Generate a final incident summary within the given length limit.
            """
