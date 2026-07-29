import pandas as pd
import numpy as np

def aplicar_estilo_alerta(val):
    """Aplica cores de fundo de acordo com o texto da coluna Status Aprovação."""
    if not isinstance(val, str):
        return ""
    val_upper = val.upper()
    if val_upper in ["A", "APROVADO"]:
        return "background-color: #e2f0d9; color: #385723; font-weight: bold;"
    elif val_upper in ["R", "REPROVADO"]:
        return "background-color: #fce4d6; color: #c00000; font-weight: bold;"
    elif val_upper in ["P", "PENDENTE"]:
        return "background-color: #fff2cc; color: #7f6000; font-weight: bold;"
    return ""

def calcular_prazo(row):
    entrega = pd.to_datetime(
        row["pc_data_entrega"],
        format="%d/%m/%Y",
        errors="coerce"
    )

    necessidade = pd.to_datetime(
        row["rm_data_necessidade"],
        format="%d/%m/%Y",
        errors="coerce"
    )

    if pd.isna(entrega) or pd.isna(necessidade):
        return "Sem Data"

    diferenca = (entrega - necessidade).days

    if diferenca == 0:
        return "Em dia"

    elif diferenca > 0:
        return f"+ {diferenca} dia(s)"

    else:
        return f"- {abs(diferenca)} dia(s)"

def processar_dataframe_compras(dados_brutos: list) -> pd.DataFrame:
    if not dados_brutos:
        return pd.DataFrame()

    df = pd.DataFrame(dados_brutos)
    #Validações temp
    print(df.columns.tolist())
    
    if "pc_comprador" in df.columns:
        print(df[["pc_numero", "pc_comprador", "pc_quantidade_comprada"]].head(20))
    #fim validações
    
    # Dicionário com a ordem estrita de todas as colunas (incluindo Data Necessidade)
    mapeamento_colunas = {
        # Requisição Mega
        "rm_usuario_solicitante": "Requisitante",
        "rm_numero": "Nr. RM",
        "rm_material": "Material",
        "rm_descricao": "Descrição",
        "rm_especificacao": "Especificação",
        "rm_motivo": "Motivo",
        "rm_qtd_solicitada": "Qt. Sol",
        "rm_unidade_medida": "Un.",
        "rm_data_emissao": "Data RM",
        "rm_data_necessidade": "Data Necessidade",
        
        # Rel do Aprovo
        #"app_status_doc": "Status Aprovação",
        #"app_nome_aprovador": "Aprovador Ocorrência",
        #"app_data_documento": "Dt de Aprovação",
        
        "rm_status_aprovacao": "Status Aprovação",
        "rm_aprovador": "Aprovador Ocorrência",
        "rm_data_aprovacao": "Dt de Aprovação",
        
        # Aprovação Pedido
        "pc_status_aprovacao": "Status Aprovação Pedido",
        "pc_aprovador": "Aprovador Pedido",
        "pc_data_aprovacao": "Dt Aprovação Pedido",
        
        
        #Pedido de compra do Mega
        "pc_comprador": "Comprador",
        "pc_numero": "Nr. Pedido",
        # Falta data de Entrega 
        "pc_quantidade_comprada": "Qt. Compr.",
        
        "pc_data_emissao": "Dt. Emissão",
        "pc_fornecedor": "Fornecedor",

       
        # Approval dos Pedidos de Compra 
        
        #"ped_situacao": "Situação Pedido",

        "ped_status_descricao": "Status Pedido",
        #"app_data_ocorrencia": "Data Ocorrência", # Ocoorencia Aprovp
        "app_nome_solicitante": "Aprovador RM",   #Rel Aprovo
        
        #"app_nome_aprovador" : "Aprovador App",
        "app_data_ocorrencia": "Dt Ocorrência", # Ocoorencia Aprovp
        #"app_status_doc": "Status App",
        
        "pc_data_entrega": "dt_entrega",
        
        # Status Final 
        "rm_situacao_item": "Status da Baixa",
        "rm_data_baixa": "Dt. Baixa",
        "status_entrega": "Prazo Entrega",
    }

    # CORREÇÃO CRUCIAL: Trocado '...' por 'coluna_banco' para forçar a criação das colunas vazias
    for coluna_banco in mapeamento_colunas.keys():
        if coluna_banco not in df.columns:
            df[coluna_banco] = None

    # Limita o tamanho do texto da descrição para não quebrar o layout da tabela
    if "rm_descricao" in df.columns:
        df["rm_descricao"] = df["rm_descricao"].fillna("None").astype(str).apply(
            lambda x: x[:30] + "..." if len(x) > 30 else x
        )

    # Formatação de todas as colunas de data no padrão brasileiro
    if "rm_data_emissao" in df.columns:
        df["rm_data_emissao"] = pd.to_datetime(df["rm_data_emissao"], errors='coerce').dt.strftime('%d/%m/%Y')
        
    if "rm_data_necessidade" in df.columns:
        df["rm_data_necessidade"] = pd.to_datetime(df["rm_data_necessidade"], errors='coerce').dt.strftime('%d/%m/%Y')
        
    #if "app_data_documento" in df.columns:
        #df["app_data_documento"] = pd.to_datetime(df["app_data_documento"], errors='coerce').dt.strftime('%d/%m/%Y')
    if "rm_data_aprovacao" in df.columns:
        df["rm_data_aprovacao"] = pd.to_datetime(
            df["rm_data_aprovacao"],
            errors="coerce"
        ).dt.strftime("%d/%m/%Y")

    if "pc_data_aprovacao" in df.columns:
        df["pc_data_aprovacao"] = pd.to_datetime(
            df["pc_data_aprovacao"],
            errors="coerce"
        ).dt.strftime("%d/%m/%Y")    
        
    if "app_data_ocorrencia" in df.columns:
        df["app_data_ocorrencia"] = pd.to_datetime(df["app_data_ocorrencia"], errors='coerce').dt.strftime('%d/%m/%Y %H:%M')
        
    if "pc_data_emissao" in df.columns:
        df["pc_data_emissao"] = (
            pd.to_datetime(
                df["pc_data_emissao"],
                errors="coerce"
            )
            .dt.strftime("%d/%m/%Y")
        )
    
    # Controla o tamanho da grade
    if "rm_especificacao" in df.columns:
        df["rm_especificacao"] = (
            df["rm_especificacao"]
            .fillna("")
            .astype(str)
            .apply(
                lambda x: x[:80] + "..."
                if len(x) > 80
                else x
            )
        )

    if "rm_motivo" in df.columns:
        df["rm_motivo"] = (
            df["rm_motivo"]
            .fillna("")
            .astype(str)
            .apply(
                lambda x: x[:80] + "..."
                if len(x) > 80
                else x
            )
        )
    
    # Formata Campos para inteiro
    if "pc_numero" in df.columns:
        df["pc_numero"] = df["pc_numero"].apply(
            lambda x: str(int(float(x))) if pd.notna(x) and str(x).strip() not in ["", "None"] else None)
    
    
    if "pc_quantidade_comprada" in df.columns:
        df["pc_quantidade_comprada"] = (
            pd.to_numeric(
                df["pc_quantidade_comprada"],
                errors="coerce"
            )
            .fillna(0)
            .astype(int)
        )


    if "rm_qtd_solicitada" in df.columns:
        df["rm_qtd_solicitada"] = (pd.to_numeric(df["rm_qtd_solicitada"], errors="coerce").fillna(0).astype(int))

    if "rm_data_baixa" in df.columns:
        df["rm_data_baixa"] = pd.to_datetime(
            df["rm_data_baixa"],
            errors="coerce"
        ).dt.strftime("%d/%m/%Y")
    
    if "pc_data_entrega" in df.columns:
        df["pc_data_entrega"] = (
            pd.to_datetime(
                df["pc_data_entrega"],
                errors="coerce"
            )
            .dt.strftime("%d/%m/%Y")
        )
    
    if "pc_data_entrega" in df.columns and "rm_data_necessidade" in df.columns:

        df["status_entrega"] = df.apply(
            calcular_prazo,
            axis=1
        )

    df_ordenado = df[
        list(mapeamento_colunas.keys())
    ].copy()

    df_final = df_ordenado.rename(
        columns=mapeamento_colunas
    )

    print(
        df_final[
            [
                "Comprador",
                "Qt. Compr.",
                "Nr. Pedido"
            ]
        ].head(30)
    )

    df_final = (
        df_final
        .replace({np.nan: "None", None: "None"})
        .astype(str)
        .replace("nan", "None")
    )

    return df_final
