-- Migration to add target attendance percentage to users table
-- Run this in Supabase SQL Editor

-- Add target_attendance column to users table
alter table users add column target_attendance numeric(5,2) default 75.00;

-- Add comment for clarity
comment on column users.target_attendance is 'Target attendance percentage for the user (e.g., 75.00 for 75%)';

-- Update existing users to have default target
update users set target_attendance = 75.00 where target_attendance is null;
