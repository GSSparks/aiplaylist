{
  description = "aiplay full-stack dev environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };
      in {
        devShells.default = pkgs.mkShell {
          name = "aiplay-dev";

          packages = with pkgs; [
            # Backend
            python311
            python311Packages.uvicorn
            python311Packages.fastapi
            openai
            ffmpeg
            python311Packages.python-dotenv

            # Frontend tooling
            nodejs_20
            nodePackages.pnpm

            # Utilities
            git
            curl
          ];

          shellHook = ''
            echo "🔊 aiplay dev shell loaded."
            echo "⚙️  Run 'pnpm install' in frontend/ to install Vite and dependencies."
          '';
        };
      });
}
