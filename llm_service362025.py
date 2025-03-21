import json
import os
import logging
import re
from datetime import datetime
from difflib import get_close_matches
from typing import Dict, Any

import requests
from langchain_community.chat_models import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import ResponseSchema, StructuredOutputParser

from .models import OCRResponse
from .utils.storage import MinioStorage

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        """
        Initialize LLM service with configuration from environment variables.
        """
        self.ollama_url = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')
        self.model = os.getenv('LLM_MODEL', 'llama3.1:8b')
        self.timeout = int(os.getenv('LLM_TIMEOUT', '30'))
        self.llm = ChatOllama(model=self.model, temperature=2, base_url=self.ollama_url)

    async def process_ocr(self, text: str, configuration: str):
        try:
            # Create prompt based on configuration
            prompt = self._create_prompt(text, configuration)
            
            # Call LLM API
            response = self._call_llm_api(prompt)
            
            # Parse response
            parsed_response = self._parse_response(response)
            
            # Classify bill category if present
            if "Bill_Category" in parsed_response:
                parsed_response["Bill_Category"] = self._classify_bill_category(
                    parsed_response["Bill_Category"], 
                    parsed_response.get("Time")
                )
            
            # Final post-processing to ensure proper formats
            parsed_response = self._post_process_response(parsed_response)
            
            return parsed_response
        except Exception as e:
            logger.error(f"Error in LLM processing: {str(e)}")
            raise

    def _create_prompt(self, text: str, configuration: str):
        print(text)
        try:
            if configuration:
                minio_storage = MinioStorage()
                get_file = minio_storage.get_configuration(f"{configuration}.txt")
                if get_file:
                    try:
                        config_text = get_file.read().decode('utf-8')
                        prompt_template = ChatPromptTemplate.from_template(config_text)
                        format_instructions = self._format_instructions()
                        prompt = prompt_template.format_messages(
                            text=text, 
                            format_instructions=format_instructions
                        )
                    except Exception as e:
                        logger.error(f"Error reading configuration file {configuration}.txt: {str(e)}")
                        prompt = f"Please process the following text, fix spelling errors, and parse to json: {text}"
                else:
                    logger.error(f"Configuration file {configuration}.txt not found")
                    prompt = f"Please process the following text, fix spelling errors, and parse to json: {text}"
            else:
                prompt = f"Please process the following text, fix spelling errors, and parse to json: {text}"
            
            return prompt
        except Exception as e:
            logger.error(f"Error creating prompt: {str(e)}")
            return text

    def _call_llm_api(self, prompt):
        try:
            response_langchain = self.llm(prompt)
            return response_langchain
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM API call failed: {str(e)}")
            raise

    def _format_instructions(self) -> str:
        Bill_Number = ResponseSchema(
        name="Bill_Number",
        description="""Extract bill number (verify it's actually a bill/invoice number, not just any number):
        - Check for "Bill No", "Invoice No", "Receipt No" labels
        - Often contains hyphens, alphanumeric combinations
        - Distinguish from "Order #"/"Order No." labeled numbers
        - When multiple candidates exist, prioritize ones with bill-related labels
        
        Examples:
        - 'Invoice#AB-65' → 'AB65'
        - 'BILLNOG0027238' → 'G0027238'
        - 'Receipt No.: 885896-ORGNL' → '885896-ORGNL'
        - 'Order No.: 12, Bill No.: 152461188' → '152461188'"""
    )
        

        Date = ResponseSchema(
            name="Date",
            description="""Convert date to mm/dd/yyyy format:
            - Identify most prominent bill date
            - Convert to consistent mm/dd/yyyy format"""
        )

        Time = ResponseSchema(
            name="Time",
            description="""Standardize time to 12-hour format:
            - Convert to 'hh:mm AA' (e.g., '10:30 PM')
            - Return empty string if no time found"""
        )

        Bill_Amount = ResponseSchema(
            name="Bill_Amount",
            description="""Extract total bill amount:
            - CRITICAL: MUST return as a NUMBER/FLOAT with 2 decimal places
            - DO NOT return as a string - must be a numeric type
            - Always add .00 for whole numbers (e.g., 100 → 100.00)
            - Look for terms like "Total", "Grand Total", "Amount Due"
            - Remove all currency symbols, commas, and other non-numeric characters
            
            Examples:
            - 1882 → 1882.00
            - ₹8,786 → 8786.00
            - $298 → 298.00
            - 500 → 500.00
            - 42.5 → 42.50""",
            type="float"
        )

        Bill_Category = ResponseSchema(
            name="Bill_Category",
            description="""Classify into most specific category:
            - Food
            - Travel (Auto/Bus/Cab)
            - Fuel
            - Communication
            - Printing & Stationery
            - Software License
            - Repairs & Maintenance
            - Staff Welfare
            - General"""
        )

        response_schemas = [Bill_Number, Date, Time, Bill_Amount, Bill_Category]
        output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
        
        additional_instructions = """
        STRICT PARSING RULES:
        1. Bill Number (NOT Order Number):
        - Look for the ACTUAL BILL/INVOICE NUMBER, not the order number
        - Bill numbers are typically longer (5+ characters) 
        - Bill numbers often appear near company header/date information
        - Order numbers are typically shorter and appear separately
        - When in doubt between multiple numbers, choose the more complex one
        - Example: In "Order #12, Invoice #885896-ORGNL", extract "885896-ORGNL" as Bill_Number

        2. Bill Amount:
        - ‼️ CRITICAL ‼️ - Must be a NUMBER (float) not a string!
        - Must ALWAYS have exactly 2 decimal places
        - Format whole numbers as: 100 → 100.00, 500 → 500.00
        - Format partial numbers as: 99.5 → 99.50, 42.1 → 42.10
        - "Error" is not a valid bill amount!
        - If multiple amounts appear, choose the one labeled as "Total" or "Grand Total"
        - Remove all currency symbols (₹,$,€,etc) and commas from amounts

        3. Formatting:
        - PURE JSON output only
        - No explanatory text
        - No errors or placeholders in values
        """
        
        format_instructions = output_parser.get_format_instructions() + additional_instructions
        return format_instructions

    def _classify_bill_category(self, category: str, time: str = None) -> str:
        category_list = [
            "Team Lunch", "Travel - Cab", "Breakfast", "Dinner", "Evening Snacks", 
            "Travel - Auto", "Travel - Bus", "Repairs & Maintenance", "Communication", 
            "General", "Printing & Stationery", "Staff Welfare", "Fuel",
            "Lunch", "Software License", "Online"
        ]

        category_lower = category.lower().strip()

        # If category contains "food" or is explicitly food
        if "food" in category_lower or category_lower == "food":
            # If time is provided, use time-based classification
            if time:
                try:
                    # Parse time with various formats
                    parsed_time = None
                    time_formats = ["%I:%M %p", "%H:%M", "%I:%M%p", "%I.%M %p", "%I.%M%p"]
                    
                    for fmt in time_formats:
                        try:
                            if "AM" in time.upper() or "PM" in time.upper():
                                parsed_time = datetime.strptime(time, fmt)
                                break
                            else:
                                # For 24-hour format
                                parsed_time = datetime.strptime(time, "%H:%M")
                                break
                        except ValueError:
                            continue
                    
                    if parsed_time:
                        hour = parsed_time.hour
                        
                        # Classify based on hour
                        if 5 <= hour < 11:
                            return "Breakfast"
                        elif 11 <= hour < 16:
                            return "Lunch"
                        elif 16 <= hour < 19:
                            return "Evening Snacks"
                        elif 19 <= hour < 23:
                            return "Dinner"
                        else:
                            return "Dinner"

                except Exception as e:
                    logger.error(f"Error classifying food category by time: {str(e)}")
                    # If time parsing fails, default to "Dinner"
                    return "Dinner"
            
            # If no time is provided, default to "Dinner" for food category
            return "Dinner"

        # For non-food categories, use existing close matching logic
        category_list_lower = [cat.lower() for cat in category_list]
        matched_category = get_close_matches(category_lower, category_list_lower, n=1, cutoff=0.3)

        if matched_category:
            classified_category = category_list[category_list_lower.index(matched_category[0])]
        else:
            classified_category = "General"
        
        return classified_category

    def _parse_response(self, response):
        try:
            raw_response = response.content
            logger.info(f"Raw LLM Response: {raw_response}")

            # Extract JSON from response using regex
            json_match = re.search(r'```json\n(.*?)\n```', raw_response, re.DOTALL)
            if json_match:
                raw_json = json_match.group(1).strip()
            else:
                raw_json = raw_response.strip()

            # Remove any inline comments and extra whitespace
            cleaned_json = re.sub(r'//.*$', '', raw_json, flags=re.MULTILINE).strip()

            try:
                parsed_response = json.loads(cleaned_json)
                
                if 'Bill_Number' in parsed_response:
                    # Improved bill number cleaning and validation
                    bill_number = parsed_response['Bill_Number']
                    
                    # Remove specific prefixes
                    prefixes_to_remove = ['BILLNO', 'Invoice', 'Receipt', 'Bill', 'No:', 'No.', 'B111', 'Bi11', '#']
                    for prefix in prefixes_to_remove:
                        if bill_number.startswith(prefix):
                            bill_number = bill_number[len(prefix):].strip()
                    
                    # Remove hash symbol if it's at the start
                    if bill_number.startswith('#'):
                        bill_number = bill_number[1:]
                    
                    # Preserve allowed symbols: hyphens, slashes, underscores, dots
                    # Remove any other special characters
                    bill_number = re.sub(r'[^a-zA-Z0-9\-/_.]', '', bill_number)
                    
                    # Validate - reject suspiciously short bill numbers (likely order numbers)
                    if len(bill_number) <= 3 and bill_number.isdigit():
                        logger.warning(f"Suspiciously short bill number detected: {bill_number}. May be an order number.")
                        # In production, you might want to set a fallback or flag this
                    
                    parsed_response['Bill_Number'] = bill_number.strip()
                
                # Bill Amount handling delegated to post-processing to ensure consistency                
                return parsed_response
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON format: {str(e)}")
                parsed_response = {"error": "Invalid JSON format", "raw_response": cleaned_json}

            return parsed_response
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            raise

    def _post_process_response(self, parsed_response):

        try:
            if 'Bill_Amount' in parsed_response:
                # Get the amount value - handle various possible types
                amount = parsed_response['Bill_Amount']
                
                # Handle error strings
                if isinstance(amount, str) and (amount.lower() == 'error' or not amount.strip()):
                    # Default to 0.00 when amount is "Error" or empty
                    logger.warning(f"Invalid bill amount detected: '{amount}'. Setting to 0.00")
                    parsed_response['Bill_Amount'] = 0.00
                    return parsed_response
                
                try:
                    # Handle string amounts (including those with currency symbols)
                    if isinstance(amount, str):
                        # Strip currency symbols, commas, spaces, and other non-numeric chars except decimal point
                        amount_cleaned = re.sub(r'[^\d.]', '', amount)
                        amount_float = float(amount_cleaned) if amount_cleaned else 0.00
                    else:
                        # Direct conversion for numeric types
                        amount_float = float(amount)
                    
                    # Format with exactly 2 decimal places using string formatting then convert back to float
                    # This ensures we get exactly 2 decimal places
                    formatted_amount = "{:.2f}".format(amount_float)
                    parsed_response['Bill_Amount'] = float(formatted_amount)
                    
                except (ValueError, TypeError) as e:
                    logger.error(f"Error converting bill amount '{amount}' to float: {str(e)}")
                    # Fallback to 0.00 on conversion errors
                    parsed_response['Bill_Amount'] = 0.00
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"Error in post-processing: {str(e)}")
            # Return the original response if post-processing fails
            return parsed_response