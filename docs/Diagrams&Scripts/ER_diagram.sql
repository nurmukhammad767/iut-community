CREATE TYPE "user_role" AS ENUM (
  'student',
  'professor',
  'admin'
);

CREATE TABLE "users" (
  "id" uuid PRIMARY KEY DEFAULT (gen_random_uuid()),
  "student_identifier" varchar(50) UNIQUE NOT NULL,
  "password_hash" varchar(255) NOT NULL,
  "full_name" varchar(100) NOT NULL,
  "role" user_role NOT NULL DEFAULT 'student',
  "created_at" timestamp DEFAULT (now())
);

CREATE TABLE "courses" (
  "id" uuid PRIMARY KEY DEFAULT (gen_random_uuid()),
  "code" varchar(20) UNIQUE NOT NULL,
  "name" varchar(100) NOT NULL
);

CREATE TABLE "course_enrollments" (
  "id" uuid PRIMARY KEY DEFAULT (gen_random_uuid()),
  "student_id" uuid,
  "course_id" uuid
);

CREATE TABLE "assignments" (
  "id" uuid PRIMARY KEY DEFAULT (gen_random_uuid()),
  "course_id" uuid,
  "title" varchar(255) NOT NULL,
  "due_date" timestamp NOT NULL,
  "status" varchar(20) DEFAULT 'active'
);

CREATE TABLE "clubs" (
  "id" uuid PRIMARY KEY DEFAULT (gen_random_uuid()),
  "name" varchar(100) UNIQUE NOT NULL,
  "description" text NOT NULL,
  "image_url" varchar(500),
  "created_by" uuid,
  "created_at" timestamp DEFAULT (now())
);

CREATE TABLE "club_members" (
  "id" uuid PRIMARY KEY DEFAULT (gen_random_uuid()),
  "club_id" uuid,
  "student_id" uuid,
  "joined_at" timestamp DEFAULT (now())
);

CREATE INDEX "idx_users_identifier" ON "users" ("student_identifier");

CREATE UNIQUE INDEX "idx_unique_enrollment" ON "course_enrollments" ("student_id", "course_id");

CREATE INDEX "idx_assignment_due_date" ON "assignments" ("due_date");

CREATE UNIQUE INDEX "idx_unique_club_member" ON "club_members" ("club_id", "student_id");

COMMENT ON COLUMN "users"."student_identifier" IS 'Can be email or university ID';

COMMENT ON COLUMN "users"."full_name" IS 'Needed to display names in Chat';

COMMENT ON COLUMN "courses"."code" IS 'e.g., CS101';

COMMENT ON COLUMN "clubs"."image_url" IS 'Stores relative path or S3 link';

COMMENT ON COLUMN "clubs"."created_by" IS 'Admin who created the club';

ALTER TABLE "course_enrollments" ADD FOREIGN KEY ("student_id") REFERENCES "users" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "course_enrollments" ADD FOREIGN KEY ("course_id") REFERENCES "courses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "assignments" ADD FOREIGN KEY ("course_id") REFERENCES "courses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "clubs" ADD FOREIGN KEY ("created_by") REFERENCES "users" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "club_members" ADD FOREIGN KEY ("club_id") REFERENCES "clubs" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "club_members" ADD FOREIGN KEY ("student_id") REFERENCES "users" ("id") DEFERRABLE INITIALLY IMMEDIATE;
