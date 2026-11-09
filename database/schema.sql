-- AI Fitness & Nutrition Platform: PostgreSQL schema
-- Generated from backend/app/models.py (SQLAlchemy). The backend creates these tables
-- automatically on startup; this file is for documentation and manual setup.
-- Run with:  psql -U fitness -d fitness_db -f database/schema.sql

-- food_items
CREATE TABLE food_items (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	category VARCHAR(40) NOT NULL, 
	serving_desc VARCHAR(60) NOT NULL, 
	serving_g FLOAT NOT NULL, 
	calories FLOAT NOT NULL, 
	protein FLOAT NOT NULL, 
	carbs FLOAT NOT NULL, 
	fat FLOAT NOT NULL, 
	fiber FLOAT NOT NULL, 
	diet_type VARCHAR(30) NOT NULL, 
	allergens VARCHAR(30)[] NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_food_nonnegative CHECK (calories >= 0 AND protein >= 0 AND carbs >= 0 AND fat >= 0), 
	CONSTRAINT ck_food_diet CHECK (diet_type IN ('vegetarian', 'non_vegetarian', 'vegan', 'eggetarian'))
);
CREATE INDEX ix_food_items_category ON food_items (category);
CREATE UNIQUE INDEX ix_food_items_name ON food_items (name);

-- meals
CREATE TABLE meals (
	id SERIAL NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	meal_type VARCHAR(20) NOT NULL, 
	diet_type VARCHAR(30) NOT NULL, 
	ingredients TEXT[] NOT NULL, 
	instructions TEXT NOT NULL, 
	calories FLOAT NOT NULL, 
	protein FLOAT NOT NULL, 
	carbs FLOAT NOT NULL, 
	fat FLOAT NOT NULL, 
	allergens VARCHAR(30)[] NOT NULL, 
	tags VARCHAR(30)[] NOT NULL, 
	prep_time_min INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_meal_type CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snacks')), 
	CONSTRAINT ck_meal_diet CHECK (diet_type IN ('vegetarian', 'non_vegetarian', 'vegan', 'eggetarian')), 
	UNIQUE (name)
);
CREATE INDEX ix_meals_meal_type ON meals (meal_type);

-- users
CREATE TABLE users (
	id SERIAL NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_users_email ON users (email);

-- workout_exercises
CREATE TABLE workout_exercises (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	category VARCHAR(20) NOT NULL, 
	target_muscle VARCHAR(80) NOT NULL, 
	equipment VARCHAR(20) NOT NULL, 
	difficulty VARCHAR(20) NOT NULL, 
	exercise_type VARCHAR(20) NOT NULL, 
	is_compound BOOLEAN NOT NULL, 
	is_timed BOOLEAN NOT NULL, 
	default_duration VARCHAR(20), 
	goal_tags VARCHAR(20)[] NOT NULL, 
	instructions TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_exercise_category CHECK (category IN ('chest', 'back', 'shoulders', 'arms', 'legs', 'core', 'full_body', 'cardio')), 
	CONSTRAINT ck_exercise_difficulty CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')), 
	CONSTRAINT ck_exercise_type CHECK (exercise_type IN ('strength', 'cardio')), 
	UNIQUE (name)
);
CREATE INDEX ix_workout_exercises_category ON workout_exercises (category);

-- food_logs
CREATE TABLE food_logs (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	food_item_id INTEGER, 
	meal_id INTEGER, 
	name VARCHAR(150) NOT NULL, 
	serving_desc VARCHAR(60) NOT NULL, 
	meal_type VARCHAR(20) NOT NULL, 
	quantity FLOAT NOT NULL, 
	amount_text VARCHAR(60), 
	log_date DATE NOT NULL, 
	calories FLOAT NOT NULL, 
	protein FLOAT NOT NULL, 
	carbs FLOAT NOT NULL, 
	fat FLOAT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_foodlog_quantity CHECK (quantity > 0 AND quantity <= 20), 
	CONSTRAINT ck_foodlog_meal_type CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snacks')), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(food_item_id) REFERENCES food_items (id) ON DELETE SET NULL, 
	FOREIGN KEY(meal_id) REFERENCES meals (id) ON DELETE SET NULL
);
CREATE INDEX ix_food_logs_user_date ON food_logs (user_id, log_date);

-- meal_recommendations
CREATE TABLE meal_recommendations (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	meal_id INTEGER NOT NULL, 
	rec_date DATE NOT NULL, 
	meal_type VARCHAR(20) NOT NULL, 
	portion FLOAT NOT NULL, 
	calories FLOAT NOT NULL, 
	protein FLOAT NOT NULL, 
	carbs FLOAT NOT NULL, 
	fat FLOAT NOT NULL, 
	match_score FLOAT NOT NULL, 
	excluded_meal_ids INTEGER[] NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_mealrec_user_date_type UNIQUE (user_id, rec_date, meal_type), 
	CONSTRAINT ck_mealrec_type CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snacks')), 
	CONSTRAINT ck_mealrec_status CHECK (status IN ('suggested', 'logged')), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(meal_id) REFERENCES meals (id) ON DELETE CASCADE
);
CREATE INDEX ix_meal_recommendations_user_id ON meal_recommendations (user_id);

-- user_profiles
CREATE TABLE user_profiles (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	age INTEGER NOT NULL, 
	gender VARCHAR(10) NOT NULL, 
	height_cm FLOAT NOT NULL, 
	weight_kg FLOAT NOT NULL, 
	target_weight_kg FLOAT NOT NULL, 
	activity_level VARCHAR(30) NOT NULL, 
	fitness_goal VARCHAR(30) NOT NULL, 
	dietary_preference VARCHAR(30) NOT NULL, 
	allergies VARCHAR(30)[] NOT NULL, 
	food_preferences TEXT, 
	workout_level VARCHAR(20) NOT NULL, 
	workout_days_per_week INTEGER NOT NULL, 
	preferred_workout_type VARCHAR(20) NOT NULL, 
	workout_split VARCHAR(20) DEFAULT 'auto' NOT NULL, 
	custom_split JSONB, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_profile_age CHECK (age BETWEEN 13 AND 100), 
	CONSTRAINT ck_profile_height CHECK (height_cm BETWEEN 100 AND 250), 
	CONSTRAINT ck_profile_weight CHECK (weight_kg BETWEEN 30 AND 300), 
	CONSTRAINT ck_profile_target CHECK (target_weight_kg BETWEEN 30 AND 300), 
	CONSTRAINT ck_profile_days CHECK (workout_days_per_week BETWEEN 2 AND 6), 
	CONSTRAINT ck_profile_gender CHECK (gender IN ('male', 'female', 'other')), 
	CONSTRAINT ck_profile_activity CHECK (activity_level IN ('sedentary', 'lightly_active', 'moderately_active', 'very_active')), 
	CONSTRAINT ck_profile_goal CHECK (fitness_goal IN ('weight_loss', 'weight_gain', 'muscle_gain', 'maintenance', 'general_fitness')), 
	CONSTRAINT ck_profile_diet CHECK (dietary_preference IN ('vegetarian', 'non_vegetarian', 'vegan', 'eggetarian')), 
	CONSTRAINT ck_profile_level CHECK (workout_level IN ('beginner', 'intermediate', 'advanced')), 
	CONSTRAINT ck_profile_wtype CHECK (preferred_workout_type IN ('gym', 'home', 'bodyweight', 'mixed', 'cardio')), 
	CONSTRAINT ck_profile_split CHECK (workout_split IN ('auto', 'full_body', 'upper_lower', 'push_pull_legs', 'bro_split', 'arnold', 'custom')), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- water_logs
CREATE TABLE water_logs (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	log_date DATE NOT NULL, 
	amount_ml INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_waterlog_amount CHECK (amount_ml > 0 AND amount_ml <= 3000), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_water_logs_user_date ON water_logs (user_id, log_date);

-- weekly_insights
CREATE TABLE weekly_insights (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	week_start DATE NOT NULL, 
	week_end DATE NOT NULL, 
	metrics JSONB NOT NULL, 
	insights JSONB NOT NULL, 
	suggestions JSONB NOT NULL, 
	behaviour JSONB NOT NULL, 
	daily JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_insight_user_week UNIQUE (user_id, week_start), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_weekly_insights_user_id ON weekly_insights (user_id);

-- weight_logs
CREATE TABLE weight_logs (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	log_date DATE NOT NULL, 
	weight_kg FLOAT NOT NULL, 
	waist_cm FLOAT, 
	chest_cm FLOAT, 
	hips_cm FLOAT, 
	arms_cm FLOAT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_weightlog_user_date UNIQUE (user_id, log_date), 
	CONSTRAINT ck_weightlog_weight CHECK (weight_kg BETWEEN 30 AND 300), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_weight_logs_user_id ON weight_logs (user_id);

-- workout_plans
CREATE TABLE workout_plans (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	days_per_week INTEGER NOT NULL, 
	level VARCHAR(20) NOT NULL, 
	goal VARCHAR(30) NOT NULL, 
	schedule INTEGER[] NOT NULL, 
	plan JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_workout_plans_user_active ON workout_plans (user_id, is_active);

-- workout_logs
CREATE TABLE workout_logs (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	plan_id INTEGER, 
	exercise_id INTEGER NOT NULL, 
	log_date DATE NOT NULL, 
	day_number INTEGER, 
	sets_completed INTEGER NOT NULL, 
	completed BOOLEAN NOT NULL, 
	sets JSONB, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_workoutlog_user_date_ex UNIQUE (user_id, log_date, exercise_id), 
	CONSTRAINT ck_workoutlog_sets CHECK (sets_completed BETWEEN 0 AND 20), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(plan_id) REFERENCES workout_plans (id) ON DELETE SET NULL, 
	FOREIGN KEY(exercise_id) REFERENCES workout_exercises (id) ON DELETE CASCADE
);
CREATE INDEX ix_workout_logs_user_date ON workout_logs (user_id, log_date);
