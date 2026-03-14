{
  description = "aiplay full-stack dev environment (simplified)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        python = pkgs.python312.withPackages (ps: with ps; [
          python-dotenv
          python-multipart
          uvicorn
          fastapi
          requests
          mutagen
        ]);

      in {
        devShells.default = pkgs.mkShell {
          name = "aiplay-dev";

          packages = with pkgs; [
            python

            # Audio / tools
            ffmpeg
            yt-dlp
            curl
            git
          ];

          shellHook = ''
            echo "🔊 aiplay dev shell loaded"
          '';
        };
      });
}
