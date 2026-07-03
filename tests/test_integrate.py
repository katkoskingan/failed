import pytest

from app.exceptions.app_exceptions import (
    DuplicateError,
    NotFoundError,
    ValidationError
)
from app.models.ticket_status import TicketStatus
from app.repositories.ticket_repository import TicketRepository
from app.repositories.user_repository import UserRepository
from app.services.ticket_service import TicketService
from app.services.user_service import UserService


class TestIntegrationScenarios:

    @pytest.fixture
    def setup_services(self):
        user_repo = UserRepository()
        ticket_repo = TicketRepository()
        user_service = UserService(user_repo)
        ticket_service = TicketService(ticket_repo, user_repo)
        return user_service, ticket_service

    @pytest.fixture
    def setup_user_and_ticket(self, setup_services):
        user_service, ticket_service = setup_services
        user = user_service.create_user("Иван Петров", "ivan@example.com")
        ticket = ticket_service.create_ticket(
            "Тестовая заявка",
            "Описание тестовой заявки",
            user.id
        )
        return user_service, ticket_service, user, ticket

    def test_create_ticket_existing_user_success(self, setup_services):
        user_service, ticket_service = setup_services
        user = user_service.create_user("Иван Петров", "ivan@example.com")
        assert user.id == 1
        assert user.is_active is True
        ticket = ticket_service.create_ticket(
            title="Проблема с входом",
            description="Не могу войти в личный кабинет",
            created_by_user_id=user.id)
        assert ticket.id == 1
        assert ticket.title == "Проблема с входом"
        assert ticket.created_by_user_id == user.id
        assert ticket.status == TicketStatus.OPEN

        saved_ticket = ticket_service.get_ticket(ticket.id)
        assert saved_ticket is not None
        assert saved_ticket.title == ticket.title

    def test_create_ticket_nonexistent_user_error(self, setup_services):
        _, ticket_service = setup_services
        with pytest.raises(NotFoundError) as exc_info:
            ticket_service.create_ticket(
                title="Тестовая заявка",
                description="Описание",
                created_by_user_id=999
            )
        assert "Пользователь с ID 999 не найден" in str(exc_info.value)

    def test_create_ticket_inactive_user_error(self, setup_services):
        user_service, ticket_service = setup_services
        user = user_service.create_user("Иван Петров", "ivan@example.com")
        deactivated_user = user_service.deactivate_user(user.id)
        assert deactivated_user.is_active is False

        with pytest.raises(ValidationError) as exc_info:
            ticket_service.create_ticket(
                title="Тестовая заявка",
                description="Описание",
                created_by_user_id=user.id)
        assert "Нельзя создать заявку для неактивного пользователя" in str(exc_info.value)

    def test_list_user_tickets_filtering(self, setup_services):
        user_service, ticket_service = setup_services
        user1 = user_service.create_user("Иван Петров", "ivan@example.com")
        user2 = user_service.create_user("Петр Иванов", "petr@example.com")
        ticket1 = ticket_service.create_ticket(
            "Заявка 1", "Описание 1", user1.id)
        ticket2 = ticket_service.create_ticket(
            "Заявка 2", "Описание 2", user1.id)
        ticket3 = ticket_service.create_ticket(
            "Заявка 3", "Описание 3", user2.id)

        user1_tickets = ticket_service.list_user_tickets(user1.id)

        assert len(user1_tickets) == 2
        assert all(t.created_by_user_id == user1.id for t in user1_tickets)
        assert ticket1 in user1_tickets
        assert ticket2 in user1_tickets
        assert ticket3 not in user1_tickets

    def test_change_ticket_status_workflow(self, setup_user_and_ticket):
        user_service, ticket_service, user, ticket = setup_user_and_ticket
        assert ticket.status == TicketStatus.OPEN

        updated_ticket = ticket_service.change_status(
            ticket.id,
            TicketStatus.IN_PROGRESS)

        assert updated_ticket.status == TicketStatus.IN_PROGRESS
        retrieved_ticket = ticket_service.get_ticket(ticket.id)
        assert retrieved_ticket.status == TicketStatus.IN_PROGRESS

        updated_ticket = ticket_service.change_status(
            ticket.id,
            TicketStatus.CLOSED
        )

        assert updated_ticket.status == TicketStatus.CLOSED
        retrieved_ticket = ticket_service.get_ticket(ticket.id)
        assert retrieved_ticket.status == TicketStatus.CLOSED

        with pytest.raises(NotFoundError) as exc_info:
            ticket_service.change_status(999, TicketStatus.CLOSED)
        assert "Заявка с ID 999 не найдена" in str(exc_info.value)

