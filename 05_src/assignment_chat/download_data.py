import duckdb
import os 


def download_data(
        repo_id:str,
        local_dir:str
        ):
    if os.path.exists(local_dir):
        print(f"Data already exists in {local_dir} - no download necessary")
    else:
        from huggingface_hub import snapshot_download
        path = snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            local_dir=local_dir
        )

        print(path)

def dump_csv(
        table_name: str = "essential_skills"
        ):

    #Download the dataset
    download_data(
        repo_id="Nason/onet-database",
        local_dir="./data/onet"
        )
    
    con = duckdb.connect("data/onet/onet.duckdb", read_only=True)

    # Print available tables
    print(con.execute("SHOW TABLES").fetchall())

    # Export a table (replace table_name with the actual table name)
    df = con.execute(f'SELECT * FROM {table_name}').fetchdf()

    df.to_csv(f"./data/onet/onet_{table_name}.csv", index=False)

    con.close()

    print(f"Saved to ./data/onet/onet_{table_name}.csv")

if __name__ == "__main__":
    table_names = ["essential_skills", "transferable_skills", "job_titles", "occupation_data"]
    for table_name in table_names:
        dump_csv(table_name=table_name)
