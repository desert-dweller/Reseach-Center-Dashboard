from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField, FloatField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models import User

# --- Authentication Forms ---

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long.')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Update Password')

# --- Admin User Management Forms ---

class AddUserForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(min=2, max=150)
    ])
    email = StringField('Email', validators=[
        DataRequired(), 
        Email()
    ])
    password = PasswordField('Password', validators=[DataRequired()])
    
    # Dropdowns ensure users can only pick valid options
    position = SelectField('Position', choices=[
        ('RA', 'Research Assistant'), 
        ('TA', 'Teaching Assistant'), 
        ('PG', 'Post Grad')
    ])
    resource_needed = SelectField('Resource', choices=[
        ('GPU', 'GPU Computing'), 
        ('CPU', 'CPU Computing')
    ])
    
    submit = SubmitField('Add User')

    # Custom Validator: Checks if username already exists
    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already exists.')

    # Custom Validator: Checks if email already exists
    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

class EditUserForm(AddUserForm):
    # Inherits fields from AddUserForm, but password is optional here
    password = PasswordField('New Password (leave blank to keep current)')
    submit = SubmitField('Update User')
    
    def __init__(self, original_username, original_email, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    # Override validation to allow keeping own username/email
    def validate_username(self, field):
        if field.data != self.original_username:
            if User.query.filter_by(username=field.data).first():
                raise ValidationError('Username already exists.')

    def validate_email(self, field):
        if field.data != self.original_email:
            if User.query.filter_by(email=field.data).first():
                raise ValidationError('Email already registered.')

# --- Server Management Forms ---

class ServerForm(FlaskForm):
    name = StringField('Server Name', validators=[DataRequired()])
    ip_address = StringField('IP Address', validators=[DataRequired()])
    location = StringField('Location')
    
    # Hardware Specs
    hdd_size = IntegerField('HDD (GB)')
    ssd_size = IntegerField('SSD (GB)')
    ram_size = IntegerField('RAM (GB)')
    vram_size = IntegerField('VRAM (GB)')
    cpu_model = StringField('CPU Model')
    gpu_model = StringField('GPU Model')
    
    submit = SubmitField('Save Server')