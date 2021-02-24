SELECT DISTINCT
	value
FROM
	package_extra
WHERE
	KEY = 'protective_marking';

UPDATE
	package_extra
SET
	value = 'protected'
WHERE
	KEY = 'protective_marking'
	AND value = 'Protected';

UPDATE
	package_extra
SET
	value = 'official'
WHERE
	KEY = 'protective_marking'
	AND value in('Unclassified', 'Public Domain');

UPDATE
	package_extra
SET
	value = 'official_sensitive'
WHERE
	KEY = 'protective_marking'
	AND value = 'Unclassified : For Office Use Only';

SELECT DISTINCT
	value
FROM
	package_extra
WHERE
	KEY = 'protective_marking';

SELECT DISTINCT
	value
FROM
	package_extra
WHERE
	KEY in('bil_confidentiality', 'bil_availability', 'bil_integrity');

UPDATE
	package_extra
SET
	value = 'exceptional'
WHERE
	KEY in('bil_confidentiality', 'bil_availability', 'bil_integrity')
	AND value = 'extreme_very_high';

UPDATE
	package_extra
SET
	value = 'serious'
WHERE
	KEY in('bil_confidentiality', 'bil_availability', 'bil_integrity')
	AND value = 'major_high';

UPDATE
	package_extra
SET
	value = 'minor'
WHERE
	KEY in('bil_confidentiality', 'bil_availability', 'bil_integrity')
	AND value = 'negligible';

UPDATE
	package_extra
SET
	value = 'limited'
WHERE
	KEY in('bil_confidentiality', 'bil_availability', 'bil_integrity')
	AND value = 'low';

UPDATE
	package_extra
SET
	value = 'n_a'
WHERE
	KEY in('bil_confidentiality', 'bil_availability', 'bil_integrity')
	AND value = 'not_yet';

SELECT DISTINCT
	value
FROM
	package_extra
WHERE
	KEY in('bil_confidentiality', 'bil_availability', 'bil_integrity')