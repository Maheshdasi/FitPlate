export const GOALS = {
  weight_loss: 'Weight loss',
  weight_gain: 'Weight gain',
  muscle_gain: 'Muscle gain',
  maintenance: 'Maintenance',
  general_fitness: 'General fitness',
}
export const DIETS = {
  vegetarian: 'Vegetarian',
  non_vegetarian: 'Non-vegetarian',
  vegan: 'Vegan',
  eggetarian: 'Eggetarian',
}
export const ACTIVITY = {
  sedentary: 'Sedentary',
  lightly_active: 'Lightly active',
  moderately_active: 'Moderately active',
  very_active: 'Very active',
}
export const ACTIVITY_HINT = {
  sedentary: 'Desk job, little or no exercise',
  lightly_active: 'Exercise 1–3 days a week',
  moderately_active: 'Exercise 3–5 days a week',
  very_active: 'Hard exercise 6–7 days a week',
}
export const LEVELS = { beginner: 'Beginner', intermediate: 'Intermediate', advanced: 'Advanced' }
export const WORKOUT_TYPES = {
  mixed: 'Mixed (gym + home)',
  gym: 'Gym',
  home: 'Home (dumbbells)',
  bodyweight: 'Bodyweight only',
  cardio: 'Cardio-focused',
}
export const ALLERGENS = ['dairy', 'eggs', 'gluten', 'nuts', 'peanuts', 'soy', 'fish', 'shellfish', 'sesame']
export const MEAL_TYPES = ['breakfast', 'lunch', 'dinner', 'snacks']
export const MEAL_LABELS = { breakfast: 'Breakfast', lunch: 'Lunch', dinner: 'Dinner', snacks: 'Snacks' }
export const CATEGORY_LABELS = {
  chest: 'Chest', back: 'Back', shoulders: 'Shoulders', arms: 'Arms', legs: 'Legs',
  core: 'Core', full_body: 'Full body', cardio: 'Cardio',
}

export const capitalize = (s) => (s ? s[0].toUpperCase() + s.slice(1) : '')
export const round = (n, d = 0) => (n == null ? '-' : Number(n).toFixed(d).replace(/\.0+$/, ''))
export const kcal = (n) => `${Math.round(n ?? 0).toLocaleString('en-IN')}`

export function shortDate(iso) {
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}
export function weekday(iso) {
  return new Date(iso + 'T00:00:00').toLocaleDateString('en-IN', { weekday: 'short' })
}
export function longDate(iso) {
  return new Date(iso + 'T00:00:00').toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })
}
export function addDays(iso, n) {
  const d = new Date(iso + 'T00:00:00')
  d.setDate(d.getDate() + n)
  const off = d.getTimezoneOffset() * 60000
  return new Date(d.getTime() - off).toISOString().slice(0, 10)
}
export const pct = (value, goal) => (goal > 0 ? Math.max(0, Math.min(100, (value / goal) * 100)) : 0)
