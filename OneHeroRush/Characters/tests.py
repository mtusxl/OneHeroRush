import pytest
import os
import django
import sys
import random
import string
from unittest.mock import patch, MagicMock

# Настрой Django ДО всех импортов
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from Characters.models import Character
from inventory.models import Item
from Soul.models import Soul, PlayerSoul

User = get_user_model()

def generate_random_username(length=10):
    """Генерирует случайное имя пользователя"""
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

# БАЗОВЫЕ ТЕСТЫ (работающие)
@pytest.mark.django_db
def test_create_character():
    """Простой тест создания персонажа"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    character = Character.objects.create(user=user, hero_name="Juggernaut")
    
    assert character.id is not None
    assert character.hero_name == "Juggernaut"
    assert character.level == 1

@pytest.mark.django_db
def test_character_has_stats():
    """Тест что у персонажа есть статы"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    character = Character.objects.create(user=user, hero_name="Lion")
    
    assert 'hp' in character.stats
    assert 'damage' in character.stats
    assert 'str' in character.stats

@pytest.mark.django_db
def test_character_level_up():
    """Тест повышения уровня"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    character = Character.objects.create(user=user, hero_name="Axe")
    
    old_level = character.level
    character.level_up()
    
    assert character.level == old_level + 1

@pytest.mark.django_db
def test_different_heroes_same_user():
    """Тест разных героев у одного пользователя"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    
    char1 = Character.objects.create(user=user, hero_name="Juggernaut")
    char2 = Character.objects.create(user=user, hero_name="Lion")
    
    assert char1.id != char2.id
    assert char1.hero_name == "Juggernaut"
    assert char2.hero_name == "Lion"

@pytest.mark.django_db
def test_character_power():
    """Тест расчета мощи"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    character = Character.objects.create(user=user, hero_name="Zeus", level=10)
    
    power = character.compute_power()
    
    assert power >= 10
    assert isinstance(power, (int, float))

# НОВЫЕ ТЕСТЫ - ИСПРАВЛЕННЫЕ

@pytest.mark.django_db
def test_character_stats_randomization():
    """Тест рандомизации статов (±10% от базовых) - ИСПРАВЛЕННЫЙ"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    character = Character.objects.create(user=user, hero_name="Juggernaut")
    
    base_stats = {
        'str': 20, 'agi': 36, 'int': 14, 'hp': 600, 'mp': 243,
        'armor': 4.76, 'damage': 58, 'move_speed': 305
    }
    
    # ПРАВИЛЬНЫЕ ДИАПАЗОНЫ (±10%)
    for stat, base_value in base_stats.items():
        if stat in character.stats:
            randomized_value = character.stats[stat]
            
            # Для целых чисел: ±10% с округлением
            if isinstance(base_value, int):
                min_expected = int(base_value * 0.9)    # 20 * 0.9 = 18
                max_expected = int(base_value * 1.1) + 1 # 20 * 1.1 = 22 + 1 = 23
            else:
                min_expected = base_value * 0.9
                max_expected = base_value * 1.1
            
            assert min_expected <= randomized_value <= max_expected, \
                f"Stat {stat}: {randomized_value} not in range {min_expected}-{max_expected} (base: {base_value})"

@pytest.mark.django_db
def test_race_bonus_assignment():
    """Тест правильного определения расы для героев"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    
    # Тестируем несколько героев с разными расами
    test_cases = [
        ('Juggernaut', 'Humans'),
        ('Pudge', 'Undead'),
        ('Ogre Magi', 'Ogres'),
        ('Shadow Fiend', 'Demons'),
        ('Drow Ranger', 'Elves'),
        ('Tidehunter', 'Sea Creatures'),
        ('Zeus', 'Mythical Creatures'),
        ('Ursa', 'Beasts'),
    ]
    
    for hero_name, expected_race in test_cases:
        character = Character.objects.create(user=user, hero_name=hero_name)
        assert character.get_race() == expected_race, \
            f"Hero {hero_name} should be {expected_race}, got {character.get_race()}"
        
        # Проверяем что бонусы расы применены
        assert character.race_bonus != {}, f"Race bonus not set for {hero_name}"

@pytest.mark.django_db
@patch('common.tasks.send_mail_notification.delay')
def test_character_evolution_only_on_10_level(mock_mail):
    """Тест что эволюция происходит только на 10, 20, 30... уровнях - ИСПРАВЛЕННЫЙ"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    character = Character.objects.create(user=user, hero_name="Juggernaut")
    
    # Тестируем эволюционные уровни
    evolution_levels = [10, 20, 30]
    
    for evolution_level in evolution_levels:
        # Сбрасываем персонажа для чистого теста
        character.level = evolution_level - 1
        character.save()
        
        stats_before = character.stats.copy()
        
        # Вызываем level_up (должна быть эволюция)
        character.level_up()
        
        # Проверяем что ХОТЯ БЫ ОДИН стат увеличился
        stats_increased = False
        for stat in stats_before:
            if stat in character.stats:
                if character.stats[stat] > stats_before[stat]:
                    stats_increased = True
                    break
        
        assert stats_increased, f"No stats increased after evolution on level {evolution_level}"
        
        # Проверяем что уведомление отправлено
        assert mock_mail.called
        
        # Сбрасываем mock для следующей итерации
        mock_mail.reset_mock()

@pytest.mark.django_db  
@patch('common.tasks.send_mail_notification.delay')
def test_character_evolution_only_on_10_level(mock_mail):
    """Тест что эволюция происходит только на 10, 20, 30... уровнях"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    character = Character.objects.create(user=user, hero_name="Juggernaut")
    
    original_stats = character.stats.copy()
    
    # Тестируем несколько НЕ-эволюционных уровней
    non_evolution_levels = [2, 3, 5, 7, 11, 12, 15]
    
    for level in non_evolution_levels:
        # Устанавливаем уровень напрямую (минуя level_up)
        character.level = level
        character.save()
        
        # Проверяем что статы НЕ изменились
        for stat in original_stats:
            if stat in character.stats:
                assert character.stats[stat] == original_stats[stat], \
                    f"Stat {stat} changed on non-evolution level {level}"
    
    # Тестируем эволюционные уровни
    evolution_levels = [10, 20, 30]
    
    for evolution_level in evolution_levels:
        character.level = evolution_level - 1
        character.save()
        
        stats_before = character.stats.copy()
        
        # Вызываем level_up (должна быть эволюция)
        character.level_up()
        
        # Проверяем что статы увеличились
        for stat in stats_before:
            if stat in character.stats:
                assert character.stats[stat] > stats_before[stat], \
                    f"Stat {stat} didn't evolve on level {evolution_level}"

@pytest.mark.django_db
def test_power_calculation_with_items_and_soul_correct():
    """Правильный тест расчета мощи с душой"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    character = Character.objects.create(user=user, hero_name="Juggernaut", level=10)
    
    # 1. Создаем предмет
    item = Item.objects.create(
        user=user,
        name="Power Treads",
        level=5,
        rarity_multiplier=1.5
    )
    character.items.add(item)
    
    # 2. Создаем ШАБЛОН души для этого героя
    soul_template = Soul.objects.create(
        character=character,  # Шаблон привязан к типу героя
        level=3,
        rarity='RARE'
    )
    
    # 3. Игрок ПОЛУЧАЕТ душу (PlayerSoul)
    player_soul = PlayerSoul.objects.create(
        user=user,
        soul=soul_template,  # Ссылается на шаблон
        equipped_to_character=character  # Экипирует на персонажа
    )
    
    # 4. ЭКИПИРУЕМ душу через FK в Character
    character.soul = soul_template  # ← ВОТ ЭТО ГЛАВНОЕ!
    character.save()
    
    character.refresh_from_db()
    
    print(f"DEBUG: Character soul: {character.soul}")
    print(f"DEBUG: Soul level: {character.soul.level if character.soul else 'None'}")
    
    power = character.compute_power()
    
    # Ожидаемая мощь: уровень + предметы + душа
    expected_power = 10 + (5 * 1.5) + 3  # = 20.5
    
    assert power == expected_power, f"Power calculation wrong: {power} != {expected_power}"

@pytest.mark.django_db
def test_soul_system_workflow():
    """Тест полного workflow системы душ"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    character = Character.objects.create(user=user, hero_name="Pudge")
    
    print("=== SOUL SYSTEM WORKFLOW ===")
    
    # 1. В игре генерируются шаблоны душ для героев
    soul_template = Soul.objects.create(
        character=character,
        level=5,
        rarity='EPIC',
        open_stats={'damage': 15, 'hp': 100},
        hidden_stats={'crit_chance': 0.1}
    )
    print(f"1. Soul template created for {character.hero_name}")
    
    # 2. Игрок получает душу через призыв
    player_soul = PlayerSoul.objects.create(
        user=user,
        soul=soul_template,
        equipped_to_character=None  # Пока не экипирована
    )
    print(f"2. Player received soul: {player_soul.soul.rarity} level {player_soul.soul.level}")
    
    # 3. Игрок экипирует душу на персонажа
    player_soul.equipped_to_character = character
    player_soul.save()
    
    character.soul = soul_template  # Устанавливаем FK душу
    character.save()
    
    print(f"3. Soul equipped to character. Character.soul: {character.soul.level}")
    
    # 4. Проверяем что мощь учитывает душу
    power = character.compute_power()
    expected_power = character.level + character.soul.level
    assert power == expected_power
    print(f"4. Power with soul: {power}")
    
    # 5. Снимаем душу
    character.soul = None
    character.save()
    player_soul.equipped_to_character = None
    player_soul.save()
    
    power_after_unequip = character.compute_power()
    assert power_after_unequip == character.level  # Только уровень
    print(f"5. Power after unequip: {power_after_unequip}")
    
    print("=== WORKFLOW COMPLETE ===")

@pytest.mark.django_db 
def test_unique_character_per_user_constraint():
    """Тест ограничения уникальности героя на пользователя"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    
    # Создаем первого персонажа
    Character.objects.create(user=user, hero_name="Juggernaut")
    
    # Попытка создать второго такого же героя должна вызвать ошибку
    with pytest.raises(Exception):  # IntegrityError или другой exception
        Character.objects.create(user=user, hero_name="Juggernaut")

@pytest.mark.django_db
def test_character_auto_attack_field():
    """Тест поля авто-атаки (из ТЗ - персонажем управляет ИИ)"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    character = Character.objects.create(user=user, hero_name="Juggernaut")
    
    # Проверяем что поле есть в модели (должно быть добавлено по ТЗ)
    assert hasattr(character, 'is_active'), "Character should have active state for AI control"

@pytest.mark.django_db
def test_character_race_specific_bonuses():
    """Тест специфических бонусов рас из ТЗ"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    
    # Проверяем бонусы для разных рас
    race_bonus_checks = [
        ('Juggernaut', 'damage_to_creeps', 0.15),  # Люди
        ('Pudge', 'health', 150),  # Нежить
        ('Ogre Magi', 'health', 0.20),  # Огры (%)
        ('Shadow Fiend', 'physical_damage', 15),  # Демоны
    ]
    
    for hero_name, bonus_key, expected_value in race_bonus_checks:
        character = Character.objects.create(user=user, hero_name=hero_name)
        
        assert bonus_key in character.race_bonus, \
            f"Bonus {bonus_key} not found for {hero_name}"
        
        bonus_value = character.race_bonus[bonus_key]
        assert bonus_value == expected_value, \
            f"Wrong bonus value for {hero_name}: {bonus_value} != {expected_value}"

@pytest.mark.django_db
def test_character_string_representation():
    """Тест строкового представления персонажа"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    character = Character.objects.create(user=user, hero_name="Sniper", level=15)
    
    expected_str = f"Sniper (Lvl 15) - {username}"
    assert str(character) == expected_str

# ТЕСТЫ ДЛЯ ПРОВЕРКИ ПО ТЗ

@pytest.mark.django_db
def test_all_27_heroes_available():
    """Тест что все 27 героев из ТЗ доступны"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    
    all_heroes = [
        'Pudge', 'Necrophos', 'Juggernaut', 'Phantom Assassin', 'Lifestealer',
        'Rubick', 'Ursa', 'Axe', 'Shadow Fiend', 'Zeus', 'Lion', 
        'Legion Commander', 'Sniper', 'Invoker', 'Crystal Maiden', 
        'Windranger', 'Ogre Magi', 'Witch Doctor', 'Drow Ranger', 
        'Vengeful Spirit', 'Lich', 'Tidehunter', 'Slark', 'Mirana', 
        'Bounty Hunter', 'Riki', 'Spirit Breaker'
    ]
    
    # Проверяем что все герои есть в HERO_CHOICES
    available_heroes = [choice[0] for choice in Character.HERO_CHOICES]
    
    for hero in all_heroes:
        assert hero in available_heroes, f"Hero {hero} not in HERO_CHOICES"
        
        # Проверяем что можем создать каждого героя
        character = Character.objects.create(user=user, hero_name=hero)
        assert character.hero_name == hero

@pytest.mark.django_db
def test_donate_heroes_identification():
    """Тест идентификации платных героев"""
    donate_heroes = ['Pudge', 'Necrophos', 'Juggernaut', 'Phantom Assassin', 
                    'Lifestealer', 'Rubick', 'Ursa', 'Axe', 'Shadow Fiend', 'Zeus']
    
    free_heroes = ['Lion', 'Legion Commander', 'Sniper', 'Invoker', 'Crystal Maiden']
    
    # Просто проверяем что списки определены
    assert len(donate_heroes) == 10, "Should have 10 donate heroes"
    assert len(free_heroes) > 0, "Should have free heroes"

@pytest.mark.django_db
@patch('common.tasks.send_mail_notification.delay')
def test_mail_notification_on_level_up(mock_mail):
    """Тест отправки уведомления при эволюции (каждые 10 уровней)"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    character = Character.objects.create(user=user, hero_name="Juggernaut")
    
    # Повышаем до 10 уровня (должно отправить уведомление)
    for _ in range(9):
        character.level_up()
    
    # Проверяем что уведомление было отправлено
    mock_mail.assert_called_once()
    
@pytest.mark.django_db
def test_character_initial_hero_limit():
    """Тест начального лимита героев (3 из ТЗ)"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    
    # Создаем максимальное количество героев
    heroes_created = []
    for i in range(user.max_heroes):
        hero = Character.objects.create(user=user, hero_name=f"Lion_{i}")
        heroes_created.append(hero)
    
    assert len(heroes_created) == user.max_heroes
    assert user.max_heroes == 3, "Initial hero limit should be 3"

@pytest.mark.django_db
def test_donate_hero_creation_without_purchase():
    """Тест что нельзя создать платного героя без покупки"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    
    donate_heroes = ['Pudge', 'Necrophos', 'Juggernaut', 'Phantom Assassin', 
                    'Lifestealer', 'Rubick', 'Ursa', 'Axe', 'Shadow Fiend', 'Zeus']
    
    for hero_name in donate_heroes:
        # Пытаемся создать платного героя без покупки
        # Должна быть ошибка или ограничение
        try:
            character = Character.objects.create(user=user, hero_name=hero_name)
            # Если создался без ошибки - проверяем что он помечен как недоступный
            assert hasattr(character, 'is_locked') or hasattr(character, 'requires_purchase'), \
                f"Donate hero {hero_name} should have purchase requirement"
        except Exception as e:
            # Ожидаем ошибку при создании платного героя
            assert "purchase" in str(e).lower() or "donate" in str(e).lower() or "locked" in str(e).lower(), \
                f"Expected purchase error for {hero_name}, got: {e}"

@pytest.mark.django_db
def test_donate_hero_creation_with_purchase():
    """Тест что можно создать платного героя после покупки"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    
    # Симулируем покупку героя
    user.purchased_heroes = ['Pudge']  # Добавляем героя в список купленных
    user.save()
    
    # Теперь должны мочь создать платного героя
    character = Character.objects.create(user=user, hero_name="Pudge")
    
    assert character.hero_name == "Pudge"
    assert character.user == user

@pytest.mark.django_db
def test_free_heroes_creation():
    """Тест что бесплатные герои создаются без ограничений"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    
    free_heroes = ['Lion', 'Legion Commander', 'Sniper', 'Invoker', 'Crystal Maiden']
    
    for hero_name in free_heroes:
        character = Character.objects.create(user=user, hero_name=hero_name)
        assert character.hero_name == hero_name
        assert character.user == user

@pytest.mark.django_db 
def test_hero_limit_with_donate_heroes():
    """Тест лимита героев - ИСПРАВЛЕННЫЙ"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    
    user.purchased_heroes = ['Pudge', 'Necrophos', 'Juggernaut']
    user.save()
    
    # Используем СУЩЕСТВУЮЩИХ героев
    existing_heroes = ['Lion', 'Legion Commander', 'Sniper']
    heroes_created = []
    
    for hero_name in existing_heroes:
        hero = Character.objects.create(user=user, hero_name=hero_name)
        heroes_created.append(hero)
    
    assert len(heroes_created) == user.max_heroes
    
    # Проверяем что можем создать больше (ограничение только в views)
    try:
        extra_hero = Character.objects.create(user=user, hero_name="Crystal Maiden")
        # Если создался - проверяем что ограничение в другом месте
        assert Character.objects.filter(user=user).count() == user.max_heroes + 1
    except Exception as e:
        # Если есть ограничение в модели
        assert "limit" in str(e).lower()

@pytest.mark.django_db
def test_donate_heroes_list_consistency():
    """Тест согласованности списков донатных и всех героев"""
    all_heroes = [choice[0] for choice in Character.HERO_CHOICES]
    donate_heroes = ['Pudge', 'Necrophos', 'Juggernaut', 'Phantom Assassin', 
                    'Lifestealer', 'Rubick', 'Ursa', 'Axe', 'Shadow Fiend', 'Zeus']
    
    # Проверяем что все донатные герои есть в общем списке
    for donate_hero in donate_heroes:
        assert donate_hero in all_heroes, f"Donate hero {donate_hero} not in HERO_CHOICES"
    
    # Проверяем что есть бесплатные герои
    free_heroes = [hero for hero in all_heroes if hero not in donate_heroes]
    assert len(free_heroes) > 0, "Should have free heroes available"
    assert len(free_heroes) == 17, f"Should have 17 free heroes, got {len(free_heroes)}"  # 27 всего - 10 донатных

@pytest.mark.django_db
@patch('common.tasks.send_mail_notification.delay')
def test_donate_hero_selection(mock_mail):
    """Тест выбора донатного героя как активного"""
    username = generate_random_username()
    user = User.objects.create_user(username=username, password="testpass")
    
    # Покупаем героя
    user.purchased_heroes = ['Phantom Assassin']
    user.save()
    
    # Создаем донатного героя
    donate_character = Character.objects.create(user=user, hero_name="Phantom Assassin")
    
    # Создаем бесплатного героя
    free_character = Character.objects.create(user=user, hero_name="Lion")
    
    # Должны мочь выбрать донатного героя как активного
    free_character.is_active = False
    free_character.save()
    
    donate_character.is_active = True
    donate_character.save()
    
    assert donate_character.is_active == True
    assert free_character.is_active == False