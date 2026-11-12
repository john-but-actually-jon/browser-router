.PHONY: deploy teardown


deploy:
	@sh scripts/osx_refresh_local_deployment.sh

teardown:
	@sh scripts/osx_remove_local_deployment.sh