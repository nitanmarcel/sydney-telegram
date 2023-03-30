FIRST_START_STRING = """
Welcome to our Chat-GPT-4 powered Telegram bot! To start, please click the "Start" button below. 

If you'd like to support our bot, please click the "Donate" button below. This will open another message with links you can use to donate. 

Thank you for choosing our bot.
"""

AGREEMENT_STRING = """
By using our Chat-GPT-4 powered Telegram bot, you agree to the following:

- You are responsible for how you use the bot and any consequences that may result from your actions.
- We are not responsible for any account bans or other issues that may arise as a result of using the bot.
"""

DONATION_STRING = """
Please note that I am not affiliated with the API provider. If you find my tool useful and would like to support its development, please consider making a donation. 
Your contributions will help me continue to improve and maintain the tool. Thank you!

- PayPal: paypal.me/marcelalexandrunitan
- Revolut: revolut.me/nitanmarcel

- BTC: 34n2cToBPuRNu6wa6UU43WTG5ZLcYaGmVq
- ETH: 0x76321e953b604b57A63014fDd7e769b23fc25De1
"""

OAUTH_STRING = """
To complete the OAuth process, please follow these steps:

1. Click the button to open the authentication link in your browser.
2. Log in to the authentication page using your credentials.
3. Once you reach a blank page with a URL in the address bar, copy the entire URL.
4. Come back to this chat and send me the copied URL in a message.

Once I receive the URL, I'll use it to complete the OAuth process.

We do not store any of your content or session information with the exception of what is necessary to provide you the service, and only with your consent.

You can always log out by running the /start command and clicking on the Logout button, from the /start command then privacy policy, or by stopping the bot.
"""

AUTHENTIFICATION_URL_NOT_VALID_STRING = """
Authentification url invalid.
"""

AUTHENTIFICATION_FAILED_STRING = """
Authentification failed.
"""

AUTHENTIFICATION_DONE_STRING = """
Authentification completed.

Here, you can ask me anything you want!

There are also two other modes you can use to ask me questions:

- Inline mode: To use inline mode, simply mention my name in any chat and type your question, ending with a question mark, exclamation mark or period. For example, "@{} What is the capital of France?" I'll respond to your question right away.

- Group mode: To use group mode, mention me or reply to one of my messages in a group chat. Remember that you'll need to be authenticated to use this mode. Once you're authenticated, you can ask me anything you want and I'll do my best to answer your question.

"""

SETTINGS_STRING = """
Here you can change your bot settings.

- Style: Choose a conversation style, between Creative, Balanced and Precise.
- Chat: Connect up to a chat that can conversate with the bot on your behalf. You need to be admin in the respective chat.
"""

CHAT_CONNECT_STRING = """
Enter the id of the chat you want to connect to.
"""

INVALID_CHAT_ID_STRING = """
The id of the entered chat is invalid.
"""

CHAT_CONNECT_NOT_ADMIN_STRING = """
You must be an admin in the target chat, before connecting your account.
"""

CHAT_ID_CONNECTED_BROADCAST_STRING = """
{} connected to this chat. Everyone in this chat can use the bot now.
"""

NOT_IN_WHITELST_STRING = """
You don\'t have access to this service! Make sure you joined and you are accepted in the waitlist.
"""

TIMEOUT_ERROR_STRING = """
Request ended with timeout error. Try again later.
"""

PROCESSING_ERROR_STRING = """
Got an unknown response from the server.
"""

CLOSE_MESSAGE_RECEIVED_STRING = """
Close message received from server.
"""

POCESSING_ALREADY_STRING = """
Processing of the last query didn't finish yet.
"""

RATELIMIT_STRING = """
Sorry, you've reached the limit of messages you can send to Bing within 24 hours. Check back soon.
"""

INLINE_NO_COOKIE_STRING = """
Sorry, you need to login first to access this service.
"""

INLINE_PROCESSING_STRING = """
Processing your query...
"""

NEW_TOPIC_CREATED_STRING = """
It's always great to start fresh. Ask me anything.
"""

TOPIC_EXPIRES_STRING = """
Topic has expired, replied message deleted, or you are not the sender of the original message.
"""

PRIVACY_STRING = """
This privacy notice outlines the ways in which we collect and process your personal data in compliance with the General Data Protection Regulation (GDPR). We are committed to protecting your privacy and ensuring that your personal data is handled in accordance with the law.

Note that this privacy notice only applies to this bot, and any other third party apis used have their own privacy notice which you can find [here](https://privacy.microsoft.com/en-us/privacystatement) and [here](https://telegram.org/privacy).

If you have any questions or concerns about our privacy practices or this privacy notice, please contact us at {}. We will be happy to address any questions or concerns you may have.
"""

PRIVACY_RETRIEVE_DATA_STRING = """
Privacy data report for {} ({}), in JSON format.

Depending on your cookies settings, even if they appear here they might be only temporary stored by the server.

If unsure, you can choose to log out and log in again.
"""

PRIVACY_DELETE_DATA_STRING = """
Are you sure you want to delete your data?

This will act the same as the logout button, deleting all your data on the bot server, including user id, cookies, chat id and settings.
"""

PRIVACY_COLLECTED_INFORMATION_STRING = """
We collect the following information:

- User ID: This is used to identify the other data in the database.
- Chat ID: This is used to connect your account to a chat so the members of the specific group can use the services. They are only stored when you connect a chat to the bot.
- Settings: These are configurations set by the user to change the bot/service response.
- Cookies: These are used to provide access to the service we use to give you the requested information. They are either stored temporarily or, if you choose, they will be stored in a database.
"""

PRIVACY_WHY_WE_COLLECT_STRING = """
We collect this information for the following reasons:

- User ID: This is necessary to identify your data in our database so that we can provide you with the requested information.
- Chat ID: This is collected to connect your account to a chat so the members of the specific group can use the services. They are only stored when you connect a chat to the bot.
- Settings: These are collected to customize the bot/service response based on your preferences.
- Cookies: These are collected to provide you with access to the service we use to give you the requested information.
"""

PRIVACY_WHAT_WE_DO_STRING = """
What do we do with your information?

We use your information to provide you with the requested information and to customize the bot/service response based on your preferences. We do not use your information for any other purposes.
"""

PRIVACY_WHAT_WE_NOT_DO_STRING = """
What do we DO NOT do with your information?

We DO NOT share your information with any third parties without your consent with the exception of the provider(s) of the services we are giving you. We do not use your information for any purposes other than those stated above.
"""

PRIVACY_RIGHT_TO_PROCESS_STRING = """
Under GDPR, you have the following rights:

- Right to access: You have the right to access your personal data that we hold.
- Right to rectification: You have the right to have any inaccurate or incomplete personal data corrected.
- Right to erasure: You have the right to have your personal data erased under certain circumstances.
- Right to restrict processing: You have the right to restrict the processing of your personal data under certain circumstances.
- Right to data portability: You have the right to receive a copy of your personal data in a structured, machine-readable format.
- Right to object: You have the right to object to the processing of your personal data under certain circumstances.
"""


PRIVACY_NO_DATA_STRING = """
'We don\'t have any of your data in our system.'
"""