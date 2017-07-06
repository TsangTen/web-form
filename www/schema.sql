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
	`recognition` bool not null,
	`block_from_beginning` bool not null,
	`block_at_midway` bool not null,
	`bug` varchar(500) not null,
	`remarks` varchar(500) not null,
	`user_name` varchar(50) not null,
	`created_at` real not null,
	key `idx_created_at` (`created_at`),
	primary key (`id`)
)engine=innodb default charset=utf8;


