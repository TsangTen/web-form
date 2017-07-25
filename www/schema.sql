drop database if exists webform;

create database webform;

use webform;

grant select, insert, update, delete on webform.* to 'www-test'@'localhost' identified by 'www-test';

create table users(
	`id` varchar(50) not null,
	`work_id` varchar(50) not null,
	`passwd` varchar(50) not null,
	`admin` bool not null,
	`name` varchar(50) not null,
	`created_at` real not null,
	unique key `idx_work_id` (`work_id`),
	key `idx_created_at` (`created_at`),
	primary key(`id`)
)engine=innodb default charset=utf8;

create table reports(
	`id` varchar(50) not null,
	`title` varchar(100) not null,
	`created_at` real not null,
	key `idx_created_at` (`created_at`),
	primary key (`id`)
)engine=innodb default charset=utf8;

create table records(
	`id` varchar(50) not null,
	`report_id` varchar(50) not null,
	`major_class` varchar(50) not null,
	`app_name` varchar(50) not null,
	`rule` varchar(50) not null,
	`type_of_change` varchar(50) not null,
	`platform` varchar(50) not null,
	`test_env` varchar(50) not null,
	`recognition` varchar(50) not null,
	`block_from_beginning` varchar(50) not null,
	`block_at_midway` varchar(50) not null,
	`bug` varchar(500) not null,
	`remarks` varchar(500) not null,
	`user_name` varchar(50) not null,
	`created_at` real not null,
	key `idx_created_at` (`created_at`),
	primary key (`id`)
)engine=innodb default charset=utf8;

create table daily(
	`id` varchar(50) not null,
	`work_id` varchar(50) not null,
	`feedback_time` varchar(50) not null,
	`feedback_way` varchar(50) not null,
	`support_type` varchar(50) not null,
	`td_num` int not null,
	`who_feedback` varchar(50) not null,
	`issue_desc` varchar(100) not null,
	`deal_time` varchar(50) not null,
	`finished` bool not null,
	`deal_desc` varchar(500) not null,
	`time_cost` real not null,
	`who` varchar(50) not null,
	`created_at` real not null,
	key `idx_created_at` (`created_at`),
	primary key (`id`)
)engine=innodb default charset=utf8;
