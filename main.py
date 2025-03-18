import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Dictionary to store user data with additional statistics
users = {}

# Dictionary to store daily bonus claims
daily_bonus = {}

# Dictionary to store admin user IDs
ADMIN_IDS = {123456789}  # Replace with actual admin Telegram IDs

# Dictionary to store withdrawal requests
withdrawal_requests = {}

# Dictionary to store user statistics
user_stats = {}

# Dictionary to store valid redeem codes and their amounts
redeem_codes = {
    'K76A9FF2RX2CMY69': 10,    # ₹10 reward
    'J5CNBERHRMYJMPV4': 20,    # ₹20 reward
    'ED6F9CHALSAZAZA9': 50,    # ₹50 reward
    '2R1R6ZM1YKT6HVMU': 100,   # ₹100 reward
    'DLBL4AOUEAJGDN85': 200,   # ₹200 reward
    '00COL9M5KJHE0HE4': 300    # ₹300 reward
}

# Set to store used redeem codes
used_codes = set()

# Constants
REFERRAL_BONUS = 10  # ₹10 per referral
MIN_WITHDRAWAL = 150  # Minimum ₹50 for withdrawal
DAILY_BONUS_AMOUNT = 25  # ₹15 daily bonus
BOT_USERNAME = "earn4cash_bot"  # Bot's username
CHANNEL_USERNAME = "@usehacktips"  # First channel username
CHANNEL_USERNAME_2 = "@JRRMODS"  # Second channel username

# Helper functions
async def check_channel_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        # Check membership for first channel
        member1 = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        is_member1 = member1.status in ['member', 'administrator', 'creator']
        
        # Check membership for second channel
        member2 = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME_2, user_id=user_id)
        is_member2 = member2.status in ['member', 'administrator', 'creator']
        
        return is_member1 and is_member2
    except Exception as e:
        logging.error(f"Error checking channel membership: {e}")
        return False

def get_join_channel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel 1", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("📢 Join Channel 2", url=f"https://t.me/{CHANNEL_USERNAME_2.replace('@', '')}")],
        [InlineKeyboardButton("✅ Check Membership", callback_data='check_membership')]
    ])

def get_main_menu_keyboard(is_admin=False):
    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data='check_balance'),
         InlineKeyboardButton("🔗 Referral Link", callback_data='get_referral')],
        [InlineKeyboardButton("💸 Withdraw", callback_data='withdraw'),
         InlineKeyboardButton("🎁 Daily Bonus", callback_data='daily_bonus')],
        [InlineKeyboardButton("📊 Leaderboard", callback_data='leaderboard'),
         InlineKeyboardButton("📈 My Stats", callback_data='my_stats')],
        [InlineKeyboardButton("ℹ️ How to Earn", callback_data='how_to_earn')]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data='admin_panel')])
    return InlineKeyboardMarkup(keyboard)

def get_back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]])

def get_join_channel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("✅ Check Membership", callback_data='check_membership')]
    ])

def get_withdrawal_options_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 UPI Payment", callback_data='withdraw_upi')],
        [InlineKeyboardButton("🎫 Redeem Code", callback_data='withdraw_redeem')],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]
    ])

def get_withdrawal_amount_keyboard():
    amounts = [100, 200, 500, 1000]
    keyboard = []
    for i in range(0, len(amounts), 2):
        row = []
        row.append(InlineKeyboardButton(f"₹{amounts[i]}", callback_data=f'amount_{amounts[i]}'))
        if i + 1 < len(amounts):
            row.append(InlineKeyboardButton(f"₹{amounts[i+1]}", callback_data=f'amount_{amounts[i+1]}'))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='withdraw')])
    return InlineKeyboardMarkup(keyboard)

def get_redeem_amount_keyboard():
    amounts = [10, 20, 50, 100, 200, 300]
    keyboard = []
    for i in range(0, len(amounts), 2):
        row = []
        row.append(InlineKeyboardButton(f"₹{amounts[i]}", callback_data=f'redeem_{amounts[i]}'))
        if i + 1 < len(amounts):
            row.append(InlineKeyboardButton(f"₹{amounts[i+1]}", callback_data=f'redeem_{amounts[i+1]}'))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='withdraw')])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    
    # Check channel membership
    if not await check_channel_membership(user_id, context):
        await update.message.reply_text(
            "🔔 Please join our channel to use the bot!",
            reply_markup=get_join_channel_keyboard()
        )
        return
    
    # Initialize user data if not exists
    if user_id not in users:
        users[user_id] = {
            'balance': 0,
            'referrals': [],
            'referred_by': None,
            'join_date': datetime.now(),
            'total_earned': 0,
            'total_withdrawn': 0,
            'last_active': datetime.now()
        }
    
    # Check if user was referred
    if context.args and len(context.args) > 0:
        referrer_id = int(context.args[0])
        if referrer_id != user_id and referrer_id in users and user_id not in users[referrer_id]['referrals']:
            users[referrer_id]['referrals'].append(user_id)
            users[referrer_id]['balance'] += REFERRAL_BONUS
            users[user_id]['referred_by'] = referrer_id
            try:
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 New referral! You earned ₹{REFERRAL_BONUS}!"
                )
            except Exception as e:
                logging.error(f"Failed to send referral notification: {e}")
    
    reply_markup = get_main_menu_keyboard()
    
    welcome_message = (
        f"Welcome {user.first_name}! 🎉\n\n"
        "I'm your Referral Earning Bot. Earn ₹10 for each successful referral!\n\n"
        "Use the buttons below to:\n"
        "- Check your balance 💰\n"
        "- Get your referral link 🔗\n"
        "- Withdraw your earnings 💸\n"
        "- Claim daily bonus 🎁\n"
        "- Learn how to earn more ℹ️"
    )
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

def get_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Pending Withdrawals", callback_data='admin_withdrawals'),
         InlineKeyboardButton("👥 User List", callback_data='admin_users')],
        [InlineKeyboardButton("🎫 Manage Codes", callback_data='admin_codes'),
         InlineKeyboardButton("📊 Statistics", callback_data='admin_stats')],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]
    ])

def get_leaderboard():
    sorted_users = sorted(users.items(), key=lambda x: len(x[1]['referrals']), reverse=True)
    return sorted_users[:10]

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    is_admin = user_id in ADMIN_IDS
    
    await query.answer()
    
    if query.data == 'check_membership':
        if await check_channel_membership(user_id, context):
            await query.message.edit_text(
                "✅ Thank you for joining! Here's the main menu:",
                reply_markup=get_main_menu_keyboard()
            )
            return
        else:
            await query.message.edit_text(
                "❌ You haven't joined our channel yet. Please join to continue:",
                reply_markup=get_join_channel_keyboard()
            )
            return
    
    # Check channel membership for all other actions
    if not await check_channel_membership(user_id, context):
        await query.message.edit_text(
            "🔔 Please join our channel to use the bot!",
            reply_markup=get_join_channel_keyboard()
        )
        return
        
    if query.data == 'back_to_menu':
        await query.message.edit_text(
            "Choose an option from the main menu:",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    if query.data == 'check_balance':
        if user_id in users:
            balance = users[user_id]['balance']
            referral_count = len(users[user_id]['referrals'])
            await query.message.edit_text(
                f"💰 Your Balance: ₹{balance}\n"
                f"👥 Total Referrals: {referral_count}",
                reply_markup=get_back_button()
            )
    
    elif query.data == 'get_referral':
        referral_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        await query.message.edit_text(
            f"🔗 Share this link to earn ₹{REFERRAL_BONUS} per referral:\n\n"
            f"{referral_link}",
            reply_markup=get_back_button()
        )
    
    elif query.data == 'withdraw':
        if user_id in users:
            balance = users[user_id]['balance']
            if balance >= MIN_WITHDRAWAL:
                await query.message.edit_text(
                    f"💰 Your Balance: ₹{balance}\n\n"
                    "Choose your withdrawal method:",
                    reply_markup=get_withdrawal_options_keyboard()
                )
            else:
                await query.message.edit_text(
                    f"❌ Minimum withdrawal amount is ₹{MIN_WITHDRAWAL}.\n"
                    f"Current balance: ₹{balance}",
                    reply_markup=get_back_button()
                )
    
    elif query.data == 'withdraw_upi':
        await query.message.edit_text(
            "Select withdrawal amount:",
            reply_markup=get_withdrawal_amount_keyboard()
        )
    
    elif query.data.startswith('redeem_'):
        amount = int(query.data.split('_')[1])
        if users[user_id]['balance'] >= amount:
            matching_code = next((code for code, value in redeem_codes.items() if value == amount), None)
            if matching_code:
                users[user_id]['balance'] -= amount
                await query.message.edit_text(
                    f"Here's your redeem code for ₹{amount}:\n\n"
                    f"`{matching_code}`\n\n"
                    "Copy and send this code to redeem your reward!\n"
                    f"New balance: ₹{users[user_id]['balance']}",
                    reply_markup=get_back_button()
                )
                context.user_data['awaiting_redeem'] = True
            else:
                await query.message.edit_text(
                    "❌ No redeem code available for this amount.",
                    reply_markup=get_back_button()
                )
        else:
            await query.message.edit_text(
                f"❌ Insufficient balance. You need ₹{amount} but have ₹{users[user_id]['balance']}.",
                reply_markup=get_back_button()
            )

    elif query.data.startswith('amount_'):
        amount = int(query.data.split('_')[1])
        if users[user_id]['balance'] >= amount:
            context.user_data['withdrawal_amount'] = amount
            await query.message.edit_text(
                f"Please enter your UPI ID to receive ₹{amount}:\n"
                "(Send your UPI ID in the next message)",
                reply_markup=get_back_button()
            )
            context.user_data['awaiting_upi'] = True
        else:
            await query.message.edit_text(
                "❌ Insufficient balance for this amount.",
                reply_markup=get_withdrawal_options_keyboard()
            )
    
    elif query.data == 'withdraw_redeem':
        await query.message.edit_text(
            "Select redeem amount:",
            reply_markup=get_redeem_amount_keyboard()
        )
    
    elif query.data == 'daily_bonus':
        now = datetime.now()
        last_claim = daily_bonus.get(user_id, None)
        
        if last_claim is None or (now - last_claim).days >= 1:
            users[user_id]['balance'] += DAILY_BONUS_AMOUNT
            daily_bonus[user_id] = now
            await query.message.edit_text(
                f"🎁 You claimed your daily bonus of ₹{DAILY_BONUS_AMOUNT}!\n"
                f"New balance: ₹{users[user_id]['balance']}",
                reply_markup=get_back_button()
            )
        else:
            next_claim = last_claim + timedelta(days=1)
            hours_left = (next_claim - now).seconds // 3600
            await query.message.edit_text(
                f"⏳ You can claim your next bonus in {hours_left} hours.",
                reply_markup=get_back_button()
            )
    
    elif query.data == 'how_to_earn':
        earning_info = (
            "💡 How to Earn:\n\n"
            f"1. Refer Friends: ₹{REFERRAL_BONUS} per referral\n"
            f"2. Daily Bonus: ₹{DAILY_BONUS_AMOUNT} every 24 hours\n\n"
            f"Minimum withdrawal: ₹{MIN_WITHDRAWAL}"
        )
        await query.message.edit_text(earning_info, reply_markup=get_back_button())

    elif query.data == 'leaderboard':
        top_users = get_leaderboard()
        leaderboard_text = "🏆 Top Referrers:\n\n"
        for i, (uid, data) in enumerate(top_users, 1):
            try:
                user = await context.bot.get_chat(uid)
                name = user.first_name
                referrals = len(data['referrals'])
                leaderboard_text += f"{i}. {name}: {referrals} referrals\n"
            except Exception:
                continue
        await query.message.edit_text(leaderboard_text, reply_markup=get_back_button())

    elif query.data == 'my_stats':
        user_data = users[user_id]
        stats = (
            "📊 Your Statistics:\n\n"
            f"Total Earned: ₹{user_data['total_earned']}\n"
            f"Total Withdrawn: ₹{user_data['total_withdrawn']}\n"
            f"Active Days: {(datetime.now() - user_data['join_date']).days}\n"
            f"Referrals: {len(user_data['referrals'])}\n"
        )
        await query.message.edit_text(stats, reply_markup=get_back_button())

    elif query.data == 'admin_panel' and is_admin:
        await query.message.edit_text("👑 Admin Panel", reply_markup=get_admin_keyboard())

    elif query.data == 'admin_withdrawals' and is_admin:
        if not withdrawal_requests:
            await query.message.edit_text("No pending withdrawals.", reply_markup=get_admin_keyboard())
        else:
            text = "📝 Pending Withdrawals:\n\n"
            for req_id, req_data in withdrawal_requests.items():
                text += f"User: {req_data['user_id']}\n"
                text += f"Amount: ₹{req_data['amount']}\n"
                text += f"UPI: {req_data['upi']}\n\n"
            await query.message.edit_text(text, reply_markup=get_admin_keyboard())

    elif query.data == 'admin_users' and is_admin:
        total_users = len(users)
        active_users = sum(1 for u in users.values() if (datetime.now() - u['last_active']).days < 7)
        text = f"👥 User Statistics:\n\nTotal Users: {total_users}\nActive Users (7d): {active_users}"
        await query.message.edit_text(text, reply_markup=get_admin_keyboard())

    elif query.data == 'admin_stats' and is_admin:
        total_withdrawn = sum(u['total_withdrawn'] for u in users.values())
        total_earned = sum(u['total_earned'] for u in users.values())
        text = (
            "📊 Platform Statistics:\n\n"
            f"Total Withdrawn: ₹{total_withdrawn}\n"
            f"Total Earned: ₹{total_earned}\n"
            f"Active Codes: {len(redeem_codes)}\n"
            f"Used Codes: {len(used_codes)}"
        )
        await query.message.edit_text(text, reply_markup=get_admin_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    message_text = update.message.text
    
    if not await check_channel_membership(user_id, context):
        await update.message.reply_text(
            "🔔 Please join our channel to use the bot!",
            reply_markup=get_join_channel_keyboard()
        )
        return
    
    if context.user_data.get('awaiting_upi'):
        amount = context.user_data.get('withdrawal_amount')
        # Process UPI withdrawal
        request_id = f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        withdrawal_requests[request_id] = {
            'user_id': user_id,
            'amount': amount,
            'upi': message_text,
            'timestamp': datetime.now()
        }
        
        await update.message.reply_text(
            f"✅ Withdrawal request received!\n\n"
            f"Request ID: {request_id}\n"
            f"Amount: ₹{amount}\n"
            f"UPI ID: {message_text}\n\n"
            "Your payment will be processed shortly.",
            reply_markup=get_main_menu_keyboard(is_admin=(user_id in ADMIN_IDS))
        )
        users[user_id]['balance'] -= amount
        users[user_id]['total_withdrawn'] += amount
        users[user_id]['last_active'] = datetime.now()
        context.user_data.pop('awaiting_upi', None)
        context.user_data.pop('withdrawal_amount', None)
    
    elif context.user_data.get('awaiting_redeem'):
        # Process redeem code
        code = message_text.strip().upper()
        if code in used_codes:
            await update.message.reply_text(
                "❌ This code has already been used!",
                reply_markup=get_main_menu_keyboard(is_admin=(user_id in ADMIN_IDS))
            )
        elif code in redeem_codes:
            amount = redeem_codes[code]
            users[user_id]['balance'] += amount
            users[user_id]['total_earned'] += amount
            users[user_id]['last_active'] = datetime.now()
            used_codes.add(code)
            del redeem_codes[code]  # Auto-delete used code
            await update.message.reply_text(
                f"✅ Code successfully redeemed!\n\n"
                f"Reward: ₹{amount}\n"
                f"New balance: ₹{users[user_id]['balance']}",
                reply_markup=get_main_menu_keyboard(is_admin=(user_id in ADMIN_IDS))
            )
        else:
            await update.message.reply_text(
                "❌ Invalid redeem code!",
                reply_markup=get_main_menu_keyboard(is_admin=(user_id in ADMIN_IDS))
            )
        context.user_data.pop('awaiting_redeem', None)

def main() -> None:
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    application = Application.builder().token('7769152908:AAH2QeJ9bnIpOjXHJIK9HNmIcf-pxYYauL0').build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()