__author__ = 'bulat'

import sqlparse
import database.cursor
from sqlparse.sql import Where, Comparison, IdentifierList, Identifier


def __table_exists(db, name):
    name = name.lower()
    return name in db.tables.keys()


def _parse(query, db, parametrs):
    query_tokens = sqlparse.parse(query)[0]

    # still no subqueries

    parsed = query_tokens
    sql_type = parsed.get_type()
    print parsed.tokens
    # Primitive checking
    if sql_type == "UNKNOWN" or sql_type is None:
        raise (BaseException("Syntax error in sql query"))

    if sql_type == "SELECT":
        # Select procedure
        proj = parsed.tokens[2]
        true_from = parsed.tokens[4]
        break_index = 2
        if str(proj).upper() == "FROM":
            break_index = 2
        elif str(true_from).upper() == "FROM":
            break_index = 4
        else:
            raise (BaseException("Can't find from keyword in select "))

        keywords = [str(token).upper() for token in query_tokens.tokens]
        # finding keywords:

        if 'ORDER' in keywords:
            break_index2 = keywords.index('ORDER')
        else:
            break_index2 = len(keywords)

        limit_index = -1
        if 'LIMIT' in keywords:
            limit_index = keywords.index('LIMIT') + 2
            limit_index = int(keywords[limit_index])

        on_index = []
        index = 0
        while 'ON' in keywords[index:]:
            index = keywords[index:].index('ON') + 2 + index
            print index
            on_index.append(index)

        print "ON INDEXES ", on_index

        where = [token for token in query_tokens.tokens if isinstance(token, Where)]
        condition = []
        comparison = []
        conditon_logic = []
        if len(where) != 0:
            condition = [token for token in where[0].tokens if str(token).upper() != "WHERE" and str(token) != ' ']
            comparison = [token for token in condition if isinstance(token, Comparison)]
            conditon_logic = [token for token in condition if not isinstance(token, Comparison)]
        tableIdent = [token for token in query_tokens.tokens[break_index:break_index2] if isinstance(token, Identifier)]
        tableList = [token for token in query_tokens.tokens[break_index:break_index2] if
                     isinstance(token, IdentifierList)]
        tables = []
        projIdent = [token for token in query_tokens.tokens[:break_index] if isinstance(token, Identifier)]
        projList = [token for token in query_tokens.tokens[:break_index] if isinstance(token, IdentifierList)]
        projections = []
        ordered = []
        ordIdent = [token for token in query_tokens.tokens[break_index2:] if isinstance(token, Identifier)]
        ordList = [token for token in query_tokens.tokens[break_index2:] if isinstance(token, IdentifierList)]

        if len(tableList) != 0:
            for t in tableList:
                for k in t.get_identifiers():
                    tables.append(str(k).lower())
        if len(tableIdent) != 0:
            for i in tableIdent:
                tables.append(str(i).lower())
        if len(tables) == 0:
            raise (BaseException("No table name identifiers provided! "))

        if len(projList) != 0:
            projections = [str(i) for i in projList[0].get_identifiers()]
        elif len(projIdent) != 0:
            projections = [str(i) for i in projIdent]

        if len(ordList) != 0:
            ordered = [str(i) for i in ordList[0].get_identifiers()]
        elif len(ordIdent) != 0:
            ordered = [str(i) for i in ordIdent]
        aliases = {}

        for ident in tables:
            poss_tab = str(ident).upper().split(' AS ')
            if len(poss_tab) > 1:
                # Can be spited
                aliases[poss_tab[1].lower()] = poss_tab[0].lower()
            else:
                aliases[poss_tab[0].lower()] = poss_tab[0].lower()

        if len(tables) > 1:
            print("Processing hash join select")
            for table_name in aliases.values():
                if not __table_exists(db, table_name):
                    raise (BaseException("No table named " + table_name))
            print tables
            i = 0
            if len(on_index) > 0:
                # there is on_index + join:
                for indx in on_index:
                    cond = query_tokens.tokens[indx]
                    all_field = str(cond).lower().split()

                    ident_field = all_field[0]
                    log_field = all_field[1]
                    cond_field = ' '.join(all_field[2:])
                    # --------- First identy
                    ident1 = ident_field.split('.')
                    true_ident1 = ''
                    alias1 = ''
                    field1 = ''
                    if len(ident1) > 1:
                        alias1 = ident1[0]
                        field1 = ident1[1]
                        true_ident1 = aliases[alias1]
                    else:
                        field1 = ident1[0]
                    print "First table is ", alias1 + true_ident1
                    print "First field if ", alias1 + field1
                    # ------ Second identy
                    ident2 = cond_field.split('.')
                    true_ident2 = ''
                    alias2 = ''
                    field2 = ''
                    if len(ident2) > 1:
                        alias2 = ident2[0]
                        field2 = ident2[1]
                        true_ident2 = aliases[alias2]
                    else:
                        field2 = ident2[0]
                    print "Second table is ", alias2 + true_ident2
                    print "Second field if ", alias2 + field2
                    local_table1 = db.tables[true_ident1.lower()]
                    local_table2 = db.tables[true_ident2.lower()]

                    if log_field == '=':
                        if proj.is_whitespace() or str(proj) == '*' or str(proj).upper() == "FROM":
                            # No projection - full select

                            if condition is not None and len(condition) != 0:
                                # TODO : Make for all. Now for one condition only
                                cond = condition[0]
                                split_field = str(cond).split()
                                indntity_field = all_field[0]
                                logic_field = all_field[1]
                                condition_field = ' '.join(all_field[2:])
                                if condition_field.lower().__contains__('%s'):
                                    condition_field = parametrs[0]
                                if logic_field == '=':
                                    # TODO : Will not work
                                    idents = indntity_field.split('.')
                                    true_ident_field = ''
                                    on_table_field = ''
                                    if len(idents) > 0:
                                        true_ident_field = idents[1]
                                        on_table_field = idents[0]
                                    else:
                                        true_ident_field = idents[0]
                                    temp_table = None
                                    other_table = None
                                    other_field = ''
                                    if on_table_field == local_table1.filename:
                                        temp_table = local_table1
                                        other_table = local_table2
                                        other_field = field2
                                    else:
                                        temp_table = local_table2
                                        other_table = local_table1
                                        other_field = field1

                                    c1 = database.cursor.select_cursor(db=temp_table, filename=temp_table.filename,
                                                                       on_field=true_ident_field,
                                                                       equal_to=condition_field)
                                    c2 = database.cursor.cursor(db=other_table, filename=other_table.filename,
                                                                on_field=other_field)

                                    c = database.cursor.join_cursor(c1, c2, temp_table.filename + '.'+ true_ident_field, other_field)
                                else:
                                    raise (BaseException("Unsupported feature"))
                            else:
                                c1 = database.cursor.cursor(db=local_table1, filename=local_table1.filename,
                                                            on_field=field1)
                                c2 = database.cursor.cursor(db=local_table2, filename=local_table2.filename,
                                                            on_field=field2)
                                c = database.cursor.join_cursor(c1, c2, true_ident1 + '.' + field1,
                                                                true_ident2 + '.' + field2)

                        elif len(projections) != 0:
                            i = 0
                         #   print projections
                         #   for i in range(len(projections)):
                         #            proc = str(projections[i]).split('.')

                         #       if len(proc) > 1:
                         #           projections[i] = aliases[proc[0]] +'.' + proc[1]
                         #   print projections
                            # ordered_on='name'
                            print("Projection select ")
                            if condition is not None and len(condition) != 0:
                                # TODO : Make for all. Now for one condition only
                                cond = condition[0]
                                split_field = str(cond).split()

                                indntity_field = split_field[0]
                                logic_field = split_field[1]
                                condition_field = ' '.join(split_field[2:])
                                if condition_field.lower().__contains__('%s'):
                                    condition_field = parametrs[0]
                                print "CONDTION ", condition_field
                                if logic_field == '=':
                                        # TODO : Will not work
                                        idents = indntity_field.split('.')
                                        true_ident_field = ''
                                        on_table_field = ''
                                        if len(idents) > 0:
                                            true_ident_field = idents[1]
                                            on_table_field = idents[0]
                                        else:
                                            true_ident_field = idents[0]
                                        temp_table = None
                                        other_table = None
                                        other_field = ''
                                        first_ident = ''
                                        sec_ident = ''
                                        if on_table_field == local_table1.filename:
                                            temp_table = local_table1
                                            other_table = local_table2
                                            other_field = field2
                                            first_ident = true_ident1
                                            sec_ident = true_ident2
                                        else:
                                            temp_table = local_table2
                                            other_table = local_table1
                                            other_field = field1
                                            first_ident = true_ident2
                                            sec_ident = true_ident1

                                        c1 = database.cursor.select_cursor(db=temp_table, filename=temp_table.filename,
                                                                           on_field=true_ident_field,
                                                                           equal_to=condition_field)
                                        c2 = database.cursor.cursor(db=other_table, filename=other_table.filename,
                                                                    on_field=other_field)

                                        c = database.cursor.join_cursor(c1, c2, first_ident + '.' + true_ident_field,
                                                                                sec_ident + '.' + other_field)
                                        condition = []
                                else:
                                    raise (BaseException("Unsupported feature"))
                            else:
                                if i == 0:
                                    c1 = database.cursor.cursor(db=local_table1, filename=local_table1.filename)
                                    c2 = database.cursor.cursor(db=local_table2, filename=local_table2.filename)
                                    c = database.cursor.join_cursor(c1, c2, true_ident1 + '.' + field1,
                                                                            true_ident2 + '.' + field2)
                                    i += 1
                                else:
                                    cs = database.cursor.cursor(db=local_table2, filename=local_table2.filename)
                                    c = database.cursor.join_cursor(c, cs, true_ident1 + '.' + field1,
                                                                            true_ident2 + '.' + field2)
                                    i += 1
                            # TODO Add here
                            #if len(ordered) != 0:
                            #    c = database.cursor.project_cursor(filename=None,
                            #                                       fields=projections, ordered_on=ordered[0],
                            #                                       on_cursor=c)
                            #else:

                            c = database.cursor.project_cursor(filename=None,
                                                               fields=projections,
                                                               on_cursor=c)
                        else:
                            raise (BaseException("Unsupported feature jet"))
                    else:
                        raise (BaseException("Wrong condition in joining "))

        else:
            # Simple select
            print("Simple select")
            table_name = tables[0]
            # print(table_name)
            if not __table_exists(db, table_name):
                raise (BaseException("No table named " + table_name))

            if proj.is_whitespace() or str(proj) == '*' or str(proj).upper() == "FROM":
                # No projection - full select
                #  c = database.cursor.select_cursor(db=db,filename=db.filename, on_field='name', greater_than=None, less_than="B")
                #
                local_table = db.tables[table_name]
                # c = database.cursor.cursor(db=local_table, filename=local_table.filename)
                if condition is not None and len(condition) != 0:
                    # TODO : Make for all. Now for one condition only
                    cond = condition[0]
                    all_field = str(cond).split()
                    ident_field = all_field[0]
                    log_field = all_field[1]
                    cond_field = ' '.join(all_field[2:])
                    if cond_field.lower().__contains__('%s'):
                             cond_field = parametrs[0]
                    if log_field == '=':
                        c = database.cursor.select_cursor(db=local_table, filename=local_table.filename,
                                                          on_field=ident_field, equal_to=cond_field)
                    else:
                        raise (BaseException("Unsupported feature"))
                else:
                    c = database.cursor.cursor(db=local_table, filename=local_table)

                if len(ordered) != 0:
                    c = database.cursor.project_cursor(filename=local_table.filename,
                                                       ordered_on=ordered[0], on_cursor=c)
                else:
                    c = database.cursor.project_cursor(filename=local_table.filename, on_cursor=c)



            elif len(projections) != 0:
                local_table = db.tables[table_name]
                # ordered_on='name'
                print("Projection select ")
                if condition is not None and len(condition) != 0:
                    # TODO : Make for all. Now for one condition only
                    cond = condition[0]
                    all_field = str(cond).split()

                    ident_field = all_field[0]
                    log_field = all_field[1]
                    cond_field = ' '.join(all_field[2:])
                    if cond_field.lower().__contains__('%s'):
                             cond_field = parametrs[0]
                    print "Condition field ", cond_field
                    if log_field == '=':
                        c = database.cursor.select_cursor(db=local_table, filename=local_table.filename,
                                                          on_field=ident_field, equal_to=cond_field)
                    else:
                        raise (BaseException("Unsupported feature"))
                else:
                    c = database.cursor.cursor(db=local_table, filename=local_table)
                if len(ordered) != 0:
                    c = database.cursor.project_cursor(filename=local_table.filename,
                                                       fields=projections, ordered_on=ordered[0],
                                                       on_cursor=c)
                else:
                    c = database.cursor.project_cursor(filename=local_table.filename,
                                                       fields=projections,
                                                       on_cursor=c)




            else:
                raise (BaseException("Syntax sql error"))
        return [c, limit_index]

    elif sql_type == "INSERT":
        pass
        # elif sql_type == ""
        # projection :
