## 1. Register ourlives app

- [x] 1.1 Add `"ourlives"` to `INSTALLED_APPS` in `project/settings.py`

## 2. Create models

- [x] 2.1 Define `Project` model: `name` (CharField max_length=100, unique=True, help_text="Project name"), `description` (TextField blank=True). Add `__str__` returning `self.name`. Meta: `verbose_name="Project"`, `verbose_name_plural="Projects"`.
- [x] 2.2 Define `InvitationCode` model: `project` (FK→Project, PROTECT, related_name="invitation_codes"), `code` (CharField max_length=50, unique=True, default=uuid_hex_callable, help_text="Auto-generated unique code. May be overridden."), `is_active` (BooleanField default=True), `max_use` (PositiveIntegerField help_text="Number of tokens this code consumes from the pool"), `current_use` (PositiveIntegerField default=0, help_text="Incremented by external service. Read-only in admin."). Add `__str__` returning `self.code == "" ? "New code" : self.code`. Meta: `verbose_name="Invitation Code"`, `verbose_name_plural="Invitation Codes"`.
- [x] 2.3 Add `CheckConstraint(name='current_use_lte_max_use', condition=Q(current_use__lte=F('max_use')))` to InvitationCode.Meta.constraints
- [x] 2.4 Define `AppSettings(SingletonModel)`: `total_tokens` (PositiveIntegerField default=0, help_text="Maximum number of tokens available across all invitation codes"). Add `__str__` returning `"App Settings"`. Meta: `verbose_name="App Settings"`.
- [x] 2.5 Add computed properties to AppSettings: `tokens_assigned` (SUM max_use), `tokens_used` (SUM current_use), `tokens_available` (total - assigned)

## 3. Add token pool validation

- [x] 3.1 Override `InvitationCode.save()`: call `full_clean()`, wrap in `transaction.atomic()`, lock AppSettings row with `select_for_update()`, compute assigned sum (excluding self on update), reject if exceeds total_tokens
- [x] 3.2 Override `InvitationCode.clean()`: validate max_use >= current_use on update
- [x] 3.3 Verify validation raises `ValidationError` with clear message in both `clean()` and `save()`

## 4. Create admin registration

- [x] 4.1 Register `ProjectAdmin(ModelAdminUnfoldBase)`: `sidebar_icon="folder"`, `list_display=("name", "description")`, `list_display_links=("name",)`, `search_fields=("name",)`
- [x] 4.2 Register `InvitationCodeAdmin(ModelAdminUnfoldBase)`: `sidebar_icon="key"`, `list_display=("code", "project", "is_active", "max_use", "current_use", "usage_percentage")`, `list_display_links=("code",)`, `list_filter=("is_active", "project")`, `search_fields=("code", "project__name")`, `readonly_fields=("current_use",)`. Add `@admin.display(description="Usage %")` method `usage_percentage(self, obj)` returning `f"{obj.current_use / obj.max_use * 100:.0f}%"` (or `"—"` if max_use=0).
- [x] 4.3 Register `AppSettingsAdmin(SingletonModelAdmin, ModelAdminUnfoldBase)`: `sidebar_icon="settings"`. Define `fieldsets` with two sections: `("Token Pool", {"fields": ("total_tokens",)})` and `("Status", {"fields": ("tokens_assigned_display", "tokens_used_display", "tokens_available_display")})`. Set `readonly_fields` to the three display method names. Add these three `@admin.display` methods: `tokens_assigned_display` returns `obj.tokens_assigned`, `tokens_used_display` returns `obj.tokens_used`, `tokens_available_display` returns `obj.tokens_available`.

## 5. Create and run migrations

- [x] 5.1 Run `python manage.py makemigrations ourlives`
- [x] 5.2 Run `python manage.py migrate ourlives`

## 6. Write tests

- [x] 6.1 Test Project creation and unique name constraint
- [x] 6.2 Test InvitationCode creation with auto-generated code
- [x] 6.3 Test token pool validation: create within limit, reject exceeding limit
- [x] 6.4 Test token pool validation: update increasing max_use, reject beyond limit
- [x] 6.5 Test token pool validation: reject max_use reduction below current_use
- [x] 6.6 Test AppSettings computed properties (assigned, used, available)
- [x] 6.7 Test AppSettings singleton behavior (get_solo returns same instance)
- [x] 6.8 Test reactivation validation: succeeds when pool has capacity, rejects when pool is full

## 7. Verify

- [x] 7.1 Run `python manage.py test ourlives`
- [x] 7.2 Run `python manage.py check --deploy`
- [x] 7.3 Run existing core tests to confirm no regressions
