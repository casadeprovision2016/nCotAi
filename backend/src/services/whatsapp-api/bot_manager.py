"""
WhatsApp Bot Manager
Manages automated bot functionality for WhatsApp integration.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class BotState(Enum):
    IDLE = "idle"
    WAITING_INPUT = "waiting_input"
    PROCESSING = "processing"
    ERROR = "error"


@dataclass
class UserSession:
    user_id: str
    phone_number: str
    state: BotState
    context: Dict[str, Any]
    last_activity: datetime
    conversation_history: List[Dict[str, Any]]


class WhatsAppBotManager:
    """Manager for WhatsApp bot functionality."""

    def __init__(self, whatsapp_service, template_manager):
        self.whatsapp_service = whatsapp_service
        self.template_manager = template_manager
        self.user_sessions: Dict[str, UserSession] = {}
        self.commands: Dict[str, Callable] = {}
        self.conversation_flows: Dict[str, Dict[str, Any]] = {}

        # Bot configuration
        self.session_timeout = timedelta(minutes=30)
        self.max_conversation_history = 50

        # Initialize bot commands and flows
        self._setup_commands()
        self._setup_conversation_flows()

    def _setup_commands(self):
        """Setup bot commands."""
        self.commands = {
            "/start": self._handle_start_command,
            "/help": self._handle_help_command,
            "/status": self._handle_status_command,
            "/editais": self._handle_editais_command,
            "/prazos": self._handle_prazos_command,
            "/cotacoes": self._handle_cotacoes_command,
            "/perfil": self._handle_perfil_command,
            "/config": self._handle_config_command,
            "/parar": self._handle_stop_command,
        }

    def _setup_conversation_flows(self):
        """Setup conversation flows."""
        self.conversation_flows = {
            "new_user_onboarding": {
                "steps": [
                    {
                        "key": "welcome",
                        "message": "Bem-vindo ao COTAI! Qual é o seu nome?",
                        "field": "name",
                    },
                    {
                        "key": "company",
                        "message": "Qual é o nome da sua empresa?",
                        "field": "company",
                    },
                    {
                        "key": "cnpj",
                        "message": "Qual é o CNPJ da sua empresa? (opcional)",
                        "field": "cnpj",
                    },
                    {
                        "key": "interests",
                        "message": "Quais tipos de editais interessam? (ex: TI, Construção, Serviços)",
                        "field": "interests",
                    },
                    {
                        "key": "complete",
                        "message": "Perfeito! Seu perfil foi configurado. Digite /help para ver os comandos disponíveis.",
                        "field": None,
                    },
                ]
            },
            "tender_subscription": {
                "steps": [
                    {
                        "key": "category",
                        "message": "Qual categoria de editais você quer acompanhar?",
                        "field": "category",
                    },
                    {
                        "key": "value_min",
                        "message": "Valor mínimo de interesse? (digite 0 para sem limite)",
                        "field": "min_value",
                    },
                    {
                        "key": "value_max",
                        "message": "Valor máximo de interesse? (digite 0 para sem limite)",
                        "field": "max_value",
                    },
                    {
                        "key": "location",
                        "message": 'Estado de interesse? (ex: SP, RJ) ou digite "todos"',
                        "field": "state",
                    },
                    {
                        "key": "complete",
                        "message": "Alerta configurado! Você receberá notificações de editais que atendam seus critérios.",
                        "field": None,
                    },
                ]
            },
            "quotation_tracking": {
                "steps": [
                    {
                        "key": "tender_id",
                        "message": "Digite o ID do edital que quer acompanhar:",
                        "field": "tender_id",
                    },
                    {
                        "key": "priority",
                        "message": "Qual a prioridade? (alta/média/baixa)",
                        "field": "priority",
                    },
                    {
                        "key": "complete",
                        "message": "Edital adicionado ao acompanhamento! Você receberá atualizações importantes.",
                        "field": None,
                    },
                ]
            },
        }

    async def process_message(
        self, phone_number: str, message: str, message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process incoming message through bot logic."""
        try:
            # Get or create user session
            session = self._get_or_create_session(phone_number)

            # Add to conversation history
            self._add_to_history(session, "user", message, message_data)

            # Check for commands
            if message.startswith("/"):
                return await self._handle_command(session, message)

            # Handle conversation flow
            if session.state == BotState.WAITING_INPUT:
                return await self._handle_conversation_flow(session, message)

            # Handle general queries
            return await self._handle_general_query(session, message)

        except Exception as e:
            logger.error(f"Error processing message from {phone_number}: {e}")
            return {"status": "error", "message": str(e)}

    async def _handle_command(
        self, session: UserSession, command: str
    ) -> Dict[str, Any]:
        """Handle bot commands."""
        command_parts = command.split()
        command_name = command_parts[0].lower()

        if command_name in self.commands:
            try:
                result = await self.commands[command_name](session, command_parts[1:])
                self._add_to_history(session, "bot", result.get("message", ""), result)
                return result
            except Exception as e:
                logger.error(f"Error handling command {command_name}: {e}")
                error_msg = "Desculpe, ocorreu um erro ao processar este comando."
                await self.whatsapp_service.send_text_message(
                    session.phone_number, error_msg
                )
                return {"status": "error", "message": error_msg}
        else:
            help_msg = "Comando não reconhecido. Digite /help para ver os comandos disponíveis."
            await self.whatsapp_service.send_text_message(
                session.phone_number, help_msg
            )
            return {"status": "unknown_command", "message": help_msg}

    async def _handle_start_command(
        self, session: UserSession, args: List[str]
    ) -> Dict[str, Any]:
        """Handle /start command."""
        # Check if user is new
        if not session.context.get("profile_complete"):
            return await self._start_conversation_flow(session, "new_user_onboarding")
        else:
            welcome_msg = f"""
👋 Olá! Bem-vindo de volta ao COTAI.

Seus comandos principais:
• /editais - Ver editais ativos
• /cotacoes - Status das cotações
• /prazos - Prazos próximos
• /help - Todos os comandos

O que posso ajudar hoje?
            """.strip()

            await self.whatsapp_service.send_text_message(
                session.phone_number, welcome_msg
            )
            return {"status": "handled", "message": welcome_msg}

    async def _handle_help_command(
        self, session: UserSession, args: List[str]
    ) -> Dict[str, Any]:
        """Handle /help command."""
        help_msg = """
🤖 *COTAI - Comandos Disponíveis*

📋 *Editais e Cotações:*
• /editais - Listar editais ativos
• /cotacoes - Status das suas cotações
• /prazos - Ver prazos próximos

🔔 *Configurações:*
• /config - Configurar alertas
• /perfil - Ver/editar perfil

ℹ️ *Informações:*
• /status - Status geral do sistema
• /help - Esta mensagem de ajuda

🛑 *Controle:*
• /parar - Pausar notificações

💬 Você também pode enviar mensagens livres - eu tentarei ajudar!
        """.strip()

        await self.whatsapp_service.send_text_message(session.phone_number, help_msg)
        return {"status": "handled", "message": help_msg}

    async def _handle_status_command(
        self, session: UserSession, args: List[str]
    ) -> Dict[str, Any]:
        """Handle /status command."""
        # This would query actual data from the database
        status_msg = """
📊 *STATUS GERAL - COTAI*

👤 *Seu Perfil:*
• Editais acompanhados: 5
• Cotações ativas: 3
• Documentos pendentes: 1

⚡ *Sistema:*
• Status: ✅ Online
• Última atualização: há 5 min
• Novos editais hoje: 12

🔗 Acesse o dashboard completo em cotai.com
        """.strip()

        await self.whatsapp_service.send_text_message(session.phone_number, status_msg)
        return {"status": "handled", "message": status_msg}

    async def _handle_editais_command(
        self, session: UserSession, args: List[str]
    ) -> Dict[str, Any]:
        """Handle /editais command."""
        # This would query actual tender data
        editais_msg = """
📋 *EDITAIS ATIVOS*

🔴 *Urgente (1-2 dias):*
• Pregão 001/2024 - Prefeitura SP
• Concorrência 005/2024 - Gov. RJ

🟡 *Em breve (3-7 dias):*
• Pregão 012/2024 - INSS
• Tomada Preços 003/2024 - UFMG

🟢 *Próximos (8+ dias):*
• 8 editais disponíveis

🔗 Ver todos no sistema COTAI
        """.strip()

        await self.whatsapp_service.send_text_message(session.phone_number, editais_msg)

        # Send interactive buttons for actions
        await self.whatsapp_service.send_interactive_message(
            to=session.phone_number,
            header="Ações Rápidas",
            body="O que você gostaria de fazer?",
            footer="COTAI Sistema",
            buttons=[
                {"id": "view_urgent", "title": "Ver Urgentes"},
                {"id": "add_alert", "title": "Criar Alerta"},
                {"id": "open_system", "title": "Abrir Sistema"},
            ],
        )

        return {"status": "handled", "message": editais_msg}

    async def _handle_prazos_command(
        self, session: UserSession, args: List[str]
    ) -> Dict[str, Any]:
        """Handle /prazos command."""
        prazos_msg = """
⏰ *PRAZOS PRÓXIMOS*

🔴 *Hoje/Amanhã:*
• Pregão TI - Prefeitura SP (amanhã 14h)

🟡 *Esta Semana:*
• Construção Hospital - Gov RJ (sex 16h)
• Serviços Limpeza - UFMG (sáb 12h)

🟢 *Próxima Semana:*
• 5 editais com prazos

⚡ *Ação necessária:* Finalize 2 propostas urgentes!
        """.strip()

        await self.whatsapp_service.send_text_message(session.phone_number, prazos_msg)
        return {"status": "handled", "message": prazos_msg}

    async def _handle_cotacoes_command(
        self, session: UserSession, args: List[str]
    ) -> Dict[str, Any]:
        """Handle /cotacoes command."""
        cotacoes_msg = """
💰 *SUAS COTAÇÕES*

📝 *Em Elaboração (2):*
• Pregão TI - 60% concluído
• Construção Escola - 30% concluído

🔍 *Em Análise (1):*
• Serviços Consultoria - Aguardando aprovação

✅ *Finalizadas (5):*
• 3 enviadas esta semana
• 2 aguardando resultado

📊 *Taxa de Sucesso:* 68% (últimos 6 meses)
        """.strip()

        await self.whatsapp_service.send_text_message(
            session.phone_number, cotacoes_msg
        )
        return {"status": "handled", "message": cotacoes_msg}

    async def _handle_perfil_command(
        self, session: UserSession, args: List[str]
    ) -> Dict[str, Any]:
        """Handle /perfil command."""
        profile = session.context.get("profile", {})

        perfil_msg = f"""
👤 *SEU PERFIL*

📝 *Informações:*
• Nome: {profile.get('name', 'Não informado')}
• Empresa: {profile.get('company', 'Não informado')}
• CNPJ: {profile.get('cnpj', 'Não informado')}

🎯 *Preferências:*
• Categorias: {profile.get('interests', 'Não configurado')}
• Alertas: {'Ativo' if profile.get('alerts_enabled', False) else 'Inativo'}

Para editar, digite /config
        """.strip()

        await self.whatsapp_service.send_text_message(session.phone_number, perfil_msg)
        return {"status": "handled", "message": perfil_msg}

    async def _handle_config_command(
        self, session: UserSession, args: List[str]
    ) -> Dict[str, Any]:
        """Handle /config command."""
        config_msg = """
⚙️ *CONFIGURAÇÕES*

Escolha o que deseja configurar:
        """.strip()

        await self.whatsapp_service.send_interactive_message(
            to=session.phone_number,
            header="Configurações",
            body=config_msg,
            footer="COTAI Sistema",
            buttons=[
                {"id": "config_alerts", "title": "Alertas"},
                {"id": "config_profile", "title": "Perfil"},
                {"id": "config_notifications", "title": "Notificações"},
            ],
        )

        return {"status": "handled", "message": config_msg}

    async def _handle_stop_command(
        self, session: UserSession, args: List[str]
    ) -> Dict[str, Any]:
        """Handle /parar command."""
        session.context["notifications_paused"] = True

        stop_msg = """
⏸️ *NOTIFICAÇÕES PAUSADAS*

Suas notificações foram pausadas temporariamente.

Para reativar:
• Digite /start
• Ou acesse as configurações no sistema

Você ainda pode usar comandos normalmente.
        """.strip()

        await self.whatsapp_service.send_text_message(session.phone_number, stop_msg)
        return {"status": "handled", "message": stop_msg}

    async def _start_conversation_flow(
        self, session: UserSession, flow_name: str
    ) -> Dict[str, Any]:
        """Start a conversation flow."""
        if flow_name not in self.conversation_flows:
            return {"status": "error", "message": "Flow not found"}

        session.state = BotState.WAITING_INPUT
        session.context["current_flow"] = flow_name
        session.context["flow_step"] = 0

        flow = self.conversation_flows[flow_name]
        first_step = flow["steps"][0]

        await self.whatsapp_service.send_text_message(
            session.phone_number, first_step["message"]
        )

        return {"status": "flow_started", "message": first_step["message"]}

    async def _handle_conversation_flow(
        self, session: UserSession, message: str
    ) -> Dict[str, Any]:
        """Handle conversation flow input."""
        flow_name = session.context.get("current_flow")
        step_index = session.context.get("flow_step", 0)

        if not flow_name or flow_name not in self.conversation_flows:
            session.state = BotState.IDLE
            return await self._handle_general_query(session, message)

        flow = self.conversation_flows[flow_name]
        steps = flow["steps"]

        if step_index >= len(steps):
            session.state = BotState.IDLE
            return await self._handle_general_query(session, message)

        current_step = steps[step_index]

        # Store user input
        if current_step["field"]:
            if "profile" not in session.context:
                session.context["profile"] = {}
            session.context["profile"][current_step["field"]] = message

        # Move to next step
        session.context["flow_step"] = step_index + 1

        if session.context["flow_step"] >= len(steps):
            # Flow completed
            session.state = BotState.IDLE
            session.context["profile_complete"] = True
            del session.context["current_flow"]
            del session.context["flow_step"]

            completion_step = steps[-1]
            await self.whatsapp_service.send_text_message(
                session.phone_number, completion_step["message"]
            )

            return {"status": "flow_completed", "message": completion_step["message"]}
        else:
            # Continue flow
            next_step = steps[session.context["flow_step"]]
            await self.whatsapp_service.send_text_message(
                session.phone_number, next_step["message"]
            )

            return {"status": "flow_continuing", "message": next_step["message"]}

    async def _handle_general_query(
        self, session: UserSession, message: str
    ) -> Dict[str, Any]:
        """Handle general queries using simple keyword matching."""
        message_lower = message.lower()

        # Simple keyword matching
        if any(word in message_lower for word in ["edital", "licitação", "pregão"]):
            return await self._handle_editais_command(session, [])
        elif any(word in message_lower for word in ["prazo", "deadline", "urgente"]):
            return await self._handle_prazos_command(session, [])
        elif any(word in message_lower for word in ["cotação", "proposta", "status"]):
            return await self._handle_cotacoes_command(session, [])
        elif any(word in message_lower for word in ["ajuda", "help", "comando"]):
            return await self._handle_help_command(session, [])
        else:
            # Default response
            default_msg = """
🤖 Não entendi bem sua pergunta.

Experimente:
• /editais - Para ver editais
• /cotacoes - Para ver suas cotações
• /help - Para ver todos os comandos

Ou seja mais específico sobre o que precisa!
            """.strip()

            await self.whatsapp_service.send_text_message(
                session.phone_number, default_msg
            )
            return {"status": "general_response", "message": default_msg}

    def _get_or_create_session(self, phone_number: str) -> UserSession:
        """Get or create user session."""
        # Clean expired sessions
        self._cleanup_expired_sessions()

        if phone_number not in self.user_sessions:
            self.user_sessions[phone_number] = UserSession(
                user_id=phone_number,  # Could be mapped to actual user ID
                phone_number=phone_number,
                state=BotState.IDLE,
                context={},
                last_activity=datetime.utcnow(),
                conversation_history=[],
            )

        session = self.user_sessions[phone_number]
        session.last_activity = datetime.utcnow()

        return session

    def _add_to_history(
        self, session: UserSession, sender: str, message: str, metadata: Dict[str, Any]
    ):
        """Add message to conversation history."""
        history_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "sender": sender,
            "message": message,
            "metadata": metadata,
        }

        session.conversation_history.append(history_entry)

        # Limit history size
        if len(session.conversation_history) > self.max_conversation_history:
            session.conversation_history = session.conversation_history[
                -self.max_conversation_history :
            ]

    def _cleanup_expired_sessions(self):
        """Clean up expired user sessions."""
        now = datetime.utcnow()
        expired_sessions = []

        for phone_number, session in self.user_sessions.items():
            if now - session.last_activity > self.session_timeout:
                expired_sessions.append(phone_number)

        for phone_number in expired_sessions:
            del self.user_sessions[phone_number]
            logger.info(f"Cleaned up expired session for {phone_number}")

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active sessions."""
        return {
            "active_sessions": len(self.user_sessions),
            "states": {
                "idle": len(
                    [s for s in self.user_sessions.values() if s.state == BotState.IDLE]
                ),
                "waiting_input": len(
                    [
                        s
                        for s in self.user_sessions.values()
                        if s.state == BotState.WAITING_INPUT
                    ]
                ),
                "processing": len(
                    [
                        s
                        for s in self.user_sessions.values()
                        if s.state == BotState.PROCESSING
                    ]
                ),
                "error": len(
                    [
                        s
                        for s in self.user_sessions.values()
                        if s.state == BotState.ERROR
                    ]
                ),
            },
            "flows_active": len(
                [s for s in self.user_sessions.values() if "current_flow" in s.context]
            ),
        }
